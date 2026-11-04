"""Migraciones numeradas. El número de versión del esquema vive en PRAGMA user_version."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import List, Tuple

CARPETA = Path(__file__).parent / "migrations"
_NOMBRE = re.compile(r"^(\d{3})_.+\.sql$")


def version_actual(con: sqlite3.Connection) -> int:
    return con.execute("PRAGMA user_version").fetchone()[0]


def migraciones_disponibles(carpeta: Path = CARPETA) -> List[Tuple[int, Path]]:
    encontradas = []
    for archivo in sorted(carpeta.glob("*.sql")):
        m = _NOMBRE.match(archivo.name)
        if m:
            encontradas.append((int(m.group(1)), archivo))
    return encontradas


def migrar(con: sqlite3.Connection, carpeta: Path = CARPETA) -> List[int]:
    """Aplica las migraciones que faltan, cada una en su propia transacción. Devuelve las aplicadas."""
    aplicadas = []
    for numero, archivo in migraciones_disponibles(carpeta):
        if numero <= version_actual(con):
            continue
        sql = archivo.read_text(encoding="utf-8")
        con.executescript(f"BEGIN;\n{sql}\nPRAGMA user_version = {numero};\nCOMMIT;")
        aplicadas.append(numero)
    return aplicadas
