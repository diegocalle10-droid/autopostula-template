"""Conexión SQLite. Es el único sitio donde se fijan los PRAGMA y se abren transacciones."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def conectar(ruta) -> sqlite3.Connection:
    """Abre (y crea si no existe) la base de datos. Autocommit: las transacciones son explícitas."""
    if str(ruta) != ":memory:":
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(ruta), isolation_level=None, timeout=5)   # espera hasta 5 s si hay otro escritor
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")      # SQLite no las aplica si no se activa
    if str(ruta) != ":memory:":
        con.execute("PRAGMA journal_mode = WAL")  # leer mientras otro proceso escribe
    return con


@contextmanager
def transaccion(con: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Una transacción por lote: si algo falla, no queda nada a medias."""
    con.execute("BEGIN IMMEDIATE")
    try:
        yield con
    except BaseException:
        con.execute("ROLLBACK")
        raise
    else:
        con.execute("COMMIT")
