from datetime import date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from portal.datos import CENTROS_COSTO, PROVEEDORES, USUARIOS, Almacen

COOKIE_SESION = "sesion_sicof"
RETARDO_CARGA_MS = 1200

plantillas = Jinja2Templates(directory=Path(__file__).parent / "plantillas")


def formato_pesos(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


plantillas.env.filters["pesos"] = formato_pesos


def validar_causacion(nit: str, factura: str, valor: str, centro: str, fecha: str) -> tuple[str | None, date | None]:
    if not factura.strip():
        return "El número de factura es obligatorio", None
    if nit.strip() not in PROVEEDORES:
        return f"El NIT {nit.strip() or '(vacío)'} no está registrado como proveedor", None
    try:
        fecha_factura = datetime.strptime(fecha.strip(), "%d/%m/%Y").date()
    except ValueError:
        return "La fecha de factura debe tener el formato dd/mm/aaaa", None
    if fecha_factura > date.today():
        return "La fecha de factura no puede ser posterior a la fecha actual", None
    if not valor.strip().isdigit() or int(valor) <= 0:
        return "El valor debe ser un número entero mayor que cero", None
    if centro not in CENTROS_COSTO:
        return "Seleccione un centro de costo válido", None
    return None, fecha_factura


def crear_app(ui: str = "v1", inestable: bool = False) -> FastAPI:
    app = FastAPI(title="SICOF", docs_url=None, redoc_url=None, openapi_url=None)
    almacen = Almacen()

    def render(request: Request, plantilla: str, status_code: int = 200, **contexto) -> HTMLResponse:
        contexto.update(ui=ui, autenticado=almacen.sesion_valida(request.cookies.get(COOKIE_SESION)))
        return plantillas.TemplateResponse(request, plantilla, contexto, status_code=status_code)

    def sin_sesion(request: Request) -> bool:
        return not almacen.sesion_valida(request.cookies.get(COOKIE_SESION))

    def formulario(request: Request, error: str | None = None, valores: dict | None = None) -> HTMLResponse:
        return render(
            request,
            "causacion_nueva.html",
            centros=CENTROS_COSTO,
            retardo_ms=RETARDO_CARGA_MS,
            error=error,
            valores=valores or {},
        )

    @app.get("/")
    def inicio(request: Request):
        destino = "/login" if sin_sesion(request) else "/causaciones/nueva"
        return RedirectResponse(destino, status_code=303)

    @app.get("/login", response_class=HTMLResponse)
    def formulario_login(request: Request):
        return render(request, "login.html", error=None)

    @app.post("/login", response_class=HTMLResponse)
    def procesar_login(
        request: Request,
        usuario: Annotated[str, Form()] = "",
        clave: Annotated[str, Form()] = "",
    ):
        if USUARIOS.get(usuario.strip()) != clave:
            return render(request, "login.html", error="Usuario o contraseña inválidos")
        respuesta = RedirectResponse("/causaciones/nueva", status_code=303)
        respuesta.set_cookie(COOKIE_SESION, almacen.abrir_sesion(), httponly=True, samesite="lax")
        return respuesta

    @app.get("/salir")
    def salir(request: Request):
        almacen.cerrar_sesion(request.cookies.get(COOKIE_SESION))
        respuesta = RedirectResponse("/login", status_code=303)
        respuesta.delete_cookie(COOKIE_SESION)
        return respuesta

    @app.get("/causaciones/nueva", response_class=HTMLResponse)
    def nueva_causacion(request: Request):
        if sin_sesion(request):
            return RedirectResponse("/login", status_code=303)
        return formulario(request)

    @app.post("/causaciones/revision", response_class=HTMLResponse)
    def revisar_causacion(
        request: Request,
        nit: Annotated[str, Form()] = "",
        factura: Annotated[str, Form()] = "",
        fecha: Annotated[str, Form()] = "",
        valor: Annotated[str, Form()] = "",
        centro: Annotated[str, Form()] = "",
    ):
        if sin_sesion(request):
            return RedirectResponse("/login", status_code=303)
        valores = {"nit": nit, "factura": factura, "fecha": fecha, "valor": valor, "centro": centro}
        error, _ = validar_causacion(nit, factura, valor, centro, fecha)
        if error:
            return formulario(request, error, valores)
        return render(
            request,
            "causacion_revision.html",
            valores=valores,
            proveedor=PROVEEDORES[nit.strip()],
            centro=CENTROS_COSTO[centro],
            valor=int(valor),
        )

    @app.post("/causaciones", response_class=HTMLResponse)
    def confirmar_causacion(
        request: Request,
        nit: Annotated[str, Form()] = "",
        factura: Annotated[str, Form()] = "",
        fecha: Annotated[str, Form()] = "",
        valor: Annotated[str, Form()] = "",
        centro: Annotated[str, Form()] = "",
    ):
        if sin_sesion(request):
            return RedirectResponse("/login", status_code=303)
        if inestable and almacen.contar_confirmacion() % 3 == 0:
            return render(request, "no_disponible.html", status_code=503)
        valores = {"nit": nit, "factura": factura, "fecha": fecha, "valor": valor, "centro": centro}
        error, fecha_factura = validar_causacion(nit, factura, valor, centro, fecha)
        if error:
            return formulario(request, error, valores)
        causacion = almacen.registrar(nit.strip(), factura.strip(), int(valor), centro, fecha_factura)
        return render(request, "causacion_registrada.html", causacion=causacion)

    @app.get("/causaciones", response_class=HTMLResponse)
    def consulta(request: Request, factura: str | None = None):
        if sin_sesion(request):
            return RedirectResponse("/login", status_code=303)
        return render(request, "causaciones.html", causaciones=almacen.buscar(factura), factura=factura or "")

    return app
