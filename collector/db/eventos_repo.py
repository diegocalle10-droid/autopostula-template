"""Acceso a `eventos`: el registro de incidentes que alimenta el disyuntor."""
from __future__ import annotations

import sqlite3
from typing import Optional


def registrar(con: sqlite3.Connection, tipo: str, ahora: str, contexto: Optional[str] = None,
              pausa_hasta: Optional[str] = None) -> None:
    con.execute("INSERT INTO eventos (ocurrido_en, tipo, contexto, pausa_hasta) VALUES (?, ?, ?, ?)",
                (ahora, tipo, contexto, pausa_hasta))


def pausa_activa(con: sqlite3.Connection, ahora: str) -> Optional[sqlite3.Row]:
    """El evento con la pausa más larga que siga vigente, o None."""
    return con.execute(
        "SELECT * FROM eventos WHERE pausa_hasta > ? ORDER BY pausa_hasta DESC LIMIT 1", (ahora,)
    ).fetchone()


def pausa_activa_con(con: sqlite3.Connection, ahora: str, marca: str) -> Optional[sqlite3.Row]:
    """Una pausa vigente cuyo contexto contiene `marca` (p. ej. «[parada_total]»), o None."""
    return con.execute("SELECT * FROM eventos WHERE pausa_hasta > ? AND contexto LIKE ? LIMIT 1",
                       (ahora, f"%{marca}%")).fetchone()


def contar(con: sqlite3.Connection, tipo: str, desde: str) -> int:
    return con.execute("SELECT COUNT(*) FROM eventos WHERE tipo = ? AND ocurrido_en >= ?", (tipo, desde)).fetchone()[0]


def contar_detalles_fallidos(con: sqlite3.Connection, desde: str) -> int:
    """Peticiones de detalle que no llegaron a guardarse (429 o error): cuentan como petición igualmente."""
    return con.execute(
        "SELECT COUNT(*) FROM eventos WHERE tipo IN ('429','fallo') AND contexto LIKE 'detail %' AND ocurrido_en >= ?",
        (desde,)).fetchone()[0]


def contar_fallos_oferta(con: sqlite3.Connection, job_id: str) -> int:
    """Veces que el detalle de esta oferta falló sin ser 429, en cualquier ejecución."""
    return con.execute("SELECT COUNT(*) FROM eventos WHERE tipo = 'fallo' AND contexto LIKE ?",
                       (f"detail {job_id}:%",)).fetchone()[0]


def cancelar_pausas(con: sqlite3.Connection, ahora: str) -> int:
    """Levanta a mano las pausas vigentes (comando `reanudar`). Devuelve cuántas había."""
    cur = con.execute("UPDATE eventos SET pausa_hasta = ? WHERE pausa_hasta > ?", (ahora, ahora))
    return cur.rowcount
