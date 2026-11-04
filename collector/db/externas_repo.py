"""Acceso a `peticiones_externas`: peticiones a LinkedIn hechas fuera del recolector."""
from __future__ import annotations

import sqlite3
from typing import Optional


def registrar(con: sqlite3.Connection, tipo: str, cantidad: int, ahora: str, nota: Optional[str] = None) -> None:
    con.execute("INSERT INTO peticiones_externas (ejecutada_en, tipo, cantidad, nota) VALUES (?, ?, ?, ?)",
                (ahora, tipo, cantidad, nota))


def contar_desde(con: sqlite3.Connection, desde: str) -> int:
    return con.execute("SELECT COALESCE(SUM(cantidad), 0) FROM peticiones_externas WHERE ejecutada_en >= ?",
                       (desde,)).fetchone()[0]
