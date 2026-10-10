import logging
import subprocess
import sys
from datetime import date

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from causaciones.cola import leer_cola
from causaciones.config import cargar_config
from causaciones.proceso import procesar_factura
from causaciones.resultados import escribir_resultados
from causaciones.sicof import ErrorCredenciales, Sicof

log = logging.getLogger("bot")

TIEMPO_ESPERA_MS = 15_000


def configurar_log(dir_salida) -> None:
    dir_salida.mkdir(parents=True, exist_ok=True)
    formato = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    for manejador in (
        logging.FileHandler(dir_salida / "bot.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ):
        manejador.setFormatter(formato)
        log.addHandler(manejador)


def lanzar_navegador(playwright, headless: bool):
    try:
        return playwright.chromium.launch(headless=headless)
    except PlaywrightError as error:
        if "Executable doesn't exist" not in str(error):
            raise
        log.info("Chromium no está instalado; instalándolo con playwright install chromium")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        return playwright.chromium.launch(headless=headless)


def main() -> int:
    config = cargar_config()
    configurar_log(config.dir_salida)

    try:
        cola = leer_cola(config.ruta_cola)
    except (FileNotFoundError, ValueError) as error:
        log.error("No se pudo leer la cola de trabajo %s: %s", config.ruta_cola, error)
        return 1
    log.info("INICIO filas_en_cola=%s portal=%s", len(cola), config.portal_url)

    resultados = []
    dir_evidencias = config.dir_salida / "evidencias"
    hoy = date.today()
    with sync_playwright() as playwright:
        navegador = lanzar_navegador(playwright, config.headless)
        pagina = navegador.new_context(locale="es-CO").new_page()
        pagina.set_default_timeout(TIEMPO_ESPERA_MS)
        pagina.set_default_navigation_timeout(TIEMPO_ESPERA_MS)
        sicof = Sicof(pagina, config.portal_url, config.usuario, config.clave)
        try:
            for fila in cola:
                resultados.append(procesar_factura(sicof, pagina, fila, hoy, dir_evidencias))
        except ErrorCredenciales as error:
            log.error("Credenciales del portal inválidas: %s", error)
            return 1
        finally:
            navegador.close()

    escribir_resultados(config.dir_salida / "resultados.xlsx", resultados)
    conteo = {}
    for r in resultados:
        conteo[r.estado] = conteo.get(r.estado, 0) + 1
    log.info("FIN procesadas=%s resumen=%s", len(resultados), conteo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
