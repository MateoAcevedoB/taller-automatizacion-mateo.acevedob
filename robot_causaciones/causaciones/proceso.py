import logging
import re
from datetime import date
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_fixed

from causaciones.modelos import CAUSADA, FALLA_SISTEMA, RECHAZADA, YA_CAUSADA, FilaCola, Resultado
from causaciones.sicof import ErrorCredenciales, FallaSistema, RechazoSicof, Sicof
from causaciones.validacion import (
    Rechazo,
    limpiar_nit,
    texto_limpio,
    validar_fecha,
    validar_valor,
)

log = logging.getLogger("bot")

MAX_INTENTOS = 3


def _es_falla_sistema(error: BaseException) -> bool:
    # PlaywrightError cubre los tiempos de espera agotados y los errores de conexión.
    return isinstance(error, (FallaSistema, PlaywrightError))


def _motivo(error: BaseException) -> str:
    texto = str(error).strip().splitlines()[0] if str(error).strip() else type(error).__name__
    return texto[:250]


def _linea(texto: str | None) -> str:
    return (texto or "").replace("\n", " ").strip()


def _registrar_resultado(r: Resultado) -> None:
    log.info(
        "FACTURA idlista=%s factura=%s nit=%s estado=%s causacion=%s detalle=%s",
        r.id_lista, r.factura, r.nit if r.nit is not None else "-", r.estado, r.causacion or "-", _linea(r.detalle) or "-",
    )


def _captura(page: Page, dir_evidencias: Path, fila: FilaCola, factura: str) -> None:
    try:
        dir_evidencias.mkdir(parents=True, exist_ok=True)
        seguro = re.sub(r"[^A-Za-z0-9_-]", "_", factura)
        page.screenshot(path=str(dir_evidencias / f"falla_{fila.id_lista}_{seguro}.png"))
    except Exception as error:  # la captura nunca debe romper el lote
        log.warning("No se pudo guardar la captura de pantalla: %s", _motivo(error))


def procesar_factura(
    sicof: Sicof, page: Page, fila: FilaCola, hoy: date, dir_evidencias: Path
) -> Resultado:
    factura = texto_limpio(fila.factura)
    nit = limpiar_nit(fila.nit)
    resultado = Resultado(fila.id_lista, factura, int(nit) if nit else None, RECHAZADA)

    try:
        # 1) Validaciones locales, antes de tocar SICOF.
        if not factura:
            raise Rechazo("El número de factura es obligatorio")
        if nit is None:
            raise Rechazo("El NIT no es válido")
        valor = validar_valor(fila.valor)
        fecha = validar_fecha(fila.fecha, hoy)
        centro = texto_limpio(fila.centro)

        # 2) Consulta + registro, con reintentos solo para fallas de sistema.
        def al_reintentar(estado) -> None:
            log.warning(
                "REINTENTO idlista=%s factura=%s intento=%s/%s motivo=%s",
                fila.id_lista, factura, estado.attempt_number + 1, MAX_INTENTOS,
                _motivo(estado.outcome.exception()),
            )

        for intento in Retrying(
            retry=retry_if_exception(_es_falla_sistema),
            stop=stop_after_attempt(MAX_INTENTOS),
            wait=wait_fixed(1),
            before_sleep=al_reintentar,
            reraise=True,
        ):
            with intento:
                sicof.asegurar_sesion()
                # Cada intento consulta antes de registrar: si un intento anterior
                # alcanzó a causar la factura, el siguiente la encuentra y no duplica.
                existente = sicof.buscar_causacion(nit, factura)
                if existente:
                    resultado.estado, resultado.causacion = YA_CAUSADA, existente
                else:
                    numero = sicof.causar(nit, factura, valor, centro, fecha.strftime("%d/%m/%Y"))
                    resultado.estado, resultado.causacion = CAUSADA, numero

    except (Rechazo, RechazoSicof) as rechazo:
        resultado.estado, resultado.detalle = RECHAZADA, str(rechazo)
    except ErrorCredenciales:
        raise
    except Exception as error:
        if _es_falla_sistema(error):
            resultado.estado = FALLA_SISTEMA
            resultado.detalle = f"Se agotaron {MAX_INTENTOS} intentos: {_motivo(error)}"
            _captura(page, dir_evidencias, fila, factura)
        else:
            log.exception("Error inesperado en la factura %s", factura)
            resultado.estado = FALLA_SISTEMA
            resultado.detalle = f"Error inesperado: {_motivo(error)}"

    _registrar_resultado(resultado)
    return resultado
