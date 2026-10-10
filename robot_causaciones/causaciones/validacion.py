import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


class Rechazo(Exception):
    """La factura no pasa las validaciones del robot (o SICOF la rechaza): no se reintenta."""


def limpiar_nit(valor: Any) -> str | None:
    """Devuelve el NIT solo con dígitos, o None si no se puede interpretar."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        texto = str(valor)
    elif isinstance(valor, float):
        if not valor.is_integer():
            return None
        texto = str(int(valor))
    else:
        texto = re.sub(r"[\s.,]", "", str(valor))
    return texto if re.fullmatch(r"[0-9]+", texto) else None


def validar_valor(valor: Any) -> int:
    mensaje = "El valor debe ser un número entero mayor que cero"
    if valor is None or isinstance(valor, bool):
        raise Rechazo(mensaje)
    texto = str(valor).strip()
    if not texto.isascii():
        raise Rechazo(mensaje)
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        raise Rechazo(mensaje) from None
    if not numero.is_finite() or numero != numero.to_integral_value() or numero <= 0:
        raise Rechazo(mensaje)
    return int(numero)


def validar_fecha(valor: Any, hoy: date) -> date:
    mensaje = "La fecha de factura no es una fecha válida yyyy-MM-dd"
    if isinstance(valor, datetime):
        fecha = valor.date()
    elif isinstance(valor, date):
        fecha = valor
    else:
        texto = "" if valor is None else str(valor).strip()
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", texto):
            raise Rechazo(mensaje)
        try:
            fecha = date.fromisoformat(texto)
        except ValueError:
            raise Rechazo(mensaje) from None
    if fecha > hoy:
        raise Rechazo("La fecha de factura es posterior al día de la ejecución")
    return fecha


def texto_limpio(valor: Any) -> str:
    """Texto sin espacios de más; un número entero llega sin '.0'."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()
