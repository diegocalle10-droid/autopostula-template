"""Conexión a Neon. La URL sale de NEON_DATABASE_URL (entorno o `.env`) y nunca se imprime."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

VARIABLE = "NEON_DATABASE_URL"


def cargar_variable(raiz: Path, nombre: str) -> Optional[str]:
    """Valor de una variable del entorno o, si no está, del `.env` de la raíz. Vacío cuenta como ausente."""
    if os.environ.get(nombre):
        return os.environ[nombre]
    env = Path(raiz) / ".env"
    if not env.exists():
        return None
    for linea in env.read_text(encoding="utf-8").splitlines():
        clave, _, valor = linea.partition("=")
        if clave.strip() == nombre and valor.strip():
            return valor.strip().strip("'\"")
    return None


def cargar_url(raiz: Path) -> Optional[str]:
    return cargar_variable(raiz, VARIABLE)


def abrir(url: str):
    import psycopg2   # import tardío: el resto del recolector funciona sin el paquete
    return psycopg2.connect(url, connect_timeout=15)


def abridor(raiz: Path) -> Optional[Callable]:
    """Función que abre una conexión a Neon, o None si falta la URL."""
    url = cargar_url(Path(raiz))
    return (lambda: abrir(url)) if url else None
