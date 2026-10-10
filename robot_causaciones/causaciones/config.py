import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    portal_url: str
    usuario: str
    clave: str
    headless: bool
    ruta_cola: Path
    dir_salida: Path


def _como_bool(texto: str) -> bool:
    return texto.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def cargar_config() -> Config:
    # Los valores por defecto coinciden con .env.example (portal local en el puerto 8020).
    load_dotenv(RAIZ / ".env")
    return Config(
        portal_url=os.getenv("PORTAL_URL", "http://127.0.0.1:8020").strip().rstrip("/"),
        usuario=os.getenv("PORTAL_USUARIO", "operador.rpa"),
        clave=os.getenv("PORTAL_CLAVE", "CxpSicof2026"),
        headless=_como_bool(os.getenv("BOT_HEADLESS", "true")),
        ruta_cola=RAIZ / "datos" / "por_radicar.xlsx",
        dir_salida=RAIZ / "salida",
    )
