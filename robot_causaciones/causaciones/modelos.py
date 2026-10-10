from dataclasses import dataclass
from typing import Any

CAUSADA = "CAUSADA"
YA_CAUSADA = "YA_CAUSADA"
RECHAZADA = "RECHAZADA"
FALLA_SISTEMA = "FALLA_SISTEMA"


@dataclass
class FilaCola:
    """Fila de PorRadicar tal como llega del libro (valores crudos, sin limpiar)."""

    id_lista: int
    factura: Any
    nit: Any
    proveedor: Any
    valor: Any
    centro: Any
    fecha: Any


@dataclass
class Resultado:
    id_lista: int
    factura: str
    nit: int | None
    estado: str
    causacion: str | None = None
    detalle: str | None = None
