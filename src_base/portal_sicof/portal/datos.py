import secrets
from dataclasses import dataclass
from datetime import date, datetime
from threading import Lock

USUARIOS = {"operador.rpa": "CxpSicof2026"}

PROVEEDORES = {
    "900123456": "Empaques del Caribe S.A.S.",
    "800234567": "Transportes Rápidos de Antioquia S.A.",
    "901345678": "Insumos Químicos del Valle S.A.S.",
    "830456789": "Servicios Tecnológicos Andinos Ltda.",
    "860567890": "Papelería y Suministros Central S.A.S.",
    "811678901": "Refrigeración Industrial del Norte S.A.S.",
}

CENTROS_COSTO = {
    "CC-100": "CC-100 Producción",
    "CC-200": "CC-200 Logística",
    "CC-300": "CC-300 Administración",
    "CC-400": "CC-400 Comercial",
}


@dataclass(frozen=True)
class Causacion:
    numero: str
    nit: str
    proveedor: str
    factura: str
    valor: int
    centro: str
    fecha_factura: date
    registrada_en: datetime


class Almacen:
    def __init__(self) -> None:
        self._causaciones: list[Causacion] = []
        self._sesiones: set[str] = set()
        self._confirmaciones = 0
        self._lock = Lock()

    def abrir_sesion(self) -> str:
        token = secrets.token_urlsafe(24)
        with self._lock:
            self._sesiones.add(token)
        return token

    def cerrar_sesion(self, token: str | None) -> None:
        with self._lock:
            self._sesiones.discard(token or "")

    def sesion_valida(self, token: str | None) -> bool:
        return bool(token) and token in self._sesiones

    def contar_confirmacion(self) -> int:
        with self._lock:
            self._confirmaciones += 1
            return self._confirmaciones

    def registrar(self, nit: str, factura: str, valor: int, centro: str, fecha_factura: date) -> Causacion:
        with self._lock:
            ahora = datetime.now()
            causacion = Causacion(
                numero=f"CXP-{ahora.year}-{len(self._causaciones) + 1:06d}",
                nit=nit,
                proveedor=PROVEEDORES[nit],
                factura=factura,
                valor=valor,
                centro=centro,
                fecha_factura=fecha_factura,
                registrada_en=ahora,
            )
            self._causaciones.append(causacion)
            return causacion

    def buscar(self, factura: str | None = None) -> list[Causacion]:
        if not factura:
            return list(self._causaciones)
        objetivo = factura.strip().upper()
        return [c for c in self._causaciones if c.factura.upper() == objetivo]
