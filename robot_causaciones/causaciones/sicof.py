import re
from urllib.parse import quote

from playwright.sync_api import Page


class FallaSistema(Exception):
    """Falla del sistema (503, tiempo de espera, conexión): se reintenta."""


class RechazoSicof(Exception):
    """SICOF rechaza la factura con un mensaje (rol alert): no se reintenta."""


class ErrorCredenciales(Exception):
    """El usuario o la clave del portal no son válidos: detiene el lote."""


class Sicof:
    """Operación de la pantalla de SICOF con localizadores por rol y etiqueta visible.

    No usa ids, clases ni estructura HTML, porque cambian entre --ui v1 y --ui v2;
    lo único que se conserva entre versiones son las etiquetas visibles.
    """

    def __init__(self, page: Page, url: str, usuario: str, clave: str) -> None:
        self.page = page
        self.url = url.rstrip("/")
        self.usuario = usuario
        self.clave = clave

    def _ir(self, ruta: str) -> None:
        respuesta = self.page.goto(self.url + ruta)
        if respuesta is not None and respuesta.status >= 500:
            raise FallaSistema(f"SICOF respondió HTTP {respuesta.status}")

    def asegurar_sesion(self) -> None:
        self._ir("/causaciones")
        if "/login" not in self.page.url:
            return
        self.page.get_by_label("Usuario", exact=True).fill(self.usuario)
        self.page.get_by_label("Contraseña", exact=True).fill(self.clave)
        self.page.get_by_role("button", name="Ingresar").click()
        pantalla_nueva = self.page.get_by_role("heading", name="Registrar causación de factura")
        alerta = self.page.get_by_role("alert")
        pantalla_nueva.or_(alerta).first.wait_for()
        if alerta.count():
            raise ErrorCredenciales(alerta.first.inner_text().strip())

    def buscar_causacion(self, nit: str, factura: str) -> str | None:
        """Número de la causación existente con el mismo NIT y número de factura, si la hay."""
        self._ir(f"/causaciones?factura={quote(factura)}")
        if "/login" in self.page.url:
            raise FallaSistema("La sesión de SICOF se perdió")
        filas = self.page.get_by_role("row").all()
        if not filas:
            raise FallaSistema("La consulta de SICOF no devolvió una tabla")
        # La primera fila es el encabezado; el resto son causaciones.
        encabezados = [t.strip() for t in filas[0].locator("th, td").all_inner_texts()]
        col_num = encabezados.index("Causación")
        col_nit = encabezados.index("NIT")
        col_fac = encabezados.index("Factura")
        for fila in filas[1:]:
            celdas = [t.strip() for t in fila.locator("td").all_inner_texts()]
            if len(celdas) != len(encabezados):
                continue  # fila de "No hay causaciones registradas"
            if celdas[col_nit] == nit and celdas[col_fac].upper() == factura.upper():
                return celdas[col_num]
        return None

    def causar(self, nit: str, factura: str, valor: int, centro: str, fecha_ddmmaaaa: str) -> str:
        """Recorre formulario, confirmación y pantalla de registro; devuelve el número CXP."""
        self._ir("/causaciones/nueva")
        pagina = self.page

        selector_centro = pagina.get_by_label("Centro de costo", exact=True)
        opciones = [t.strip() for t in selector_centro.locator("option").all_text_contents()]
        opcion = next((o for o in opciones if o.split(" ")[0] == centro), None)
        if opcion is None:
            raise RechazoSicof(f"El centro de costo {centro or '(vacío)'} no existe en la lista de SICOF")

        # fill y select_option esperan solos a que el formulario termine de cargar.
        pagina.get_by_label("Número de factura", exact=True).fill(factura)
        pagina.get_by_label("NIT del proveedor", exact=True).fill(nit)
        selector_centro.select_option(label=opcion)
        pagina.get_by_label("Valor total", exact=True).fill(str(valor))
        pagina.get_by_label("Fecha de factura", exact=True).fill(fecha_ddmmaaaa)
        pagina.get_by_role("button", name="Continuar").click()

        confirmar = pagina.get_by_role("button", name="Confirmar causación")
        alerta = pagina.get_by_role("alert")
        confirmar.or_(alerta).first.wait_for()
        if alerta.count():
            raise RechazoSicof(alerta.first.inner_text().strip())
        confirmar.click()

        registrada = pagina.get_by_role("heading", name="Causación registrada")
        no_disponible = pagina.get_by_role("heading", name="Servicio temporalmente no disponible")
        registrada.or_(no_disponible).or_(alerta).first.wait_for()
        if no_disponible.count():
            raise FallaSistema("SICOF: Servicio temporalmente no disponible")
        if alerta.count():
            raise RechazoSicof(alerta.first.inner_text().strip())
        numero = re.search(r"CXP-\d{4}-\d{6}", pagina.locator("body").inner_text())
        if numero is None:
            raise FallaSistema("No se encontró el número de causación en la pantalla")
        return numero.group(0)
