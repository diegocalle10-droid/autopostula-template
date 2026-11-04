"""Acceso a `consultas` (diario de peticiones) y `hallazgos` (qué consulta encontró qué oferta)."""
from __future__ import annotations

import sqlite3
from typing import List, Optional


def registrar(con: sqlite3.Connection, combinacion_id: int, pagina: int, jobage_dias: int, ahora: str,
              resultado: str, n_resultados: Optional[int] = None, codigo_error: Optional[str] = None) -> int:
    cur = con.execute(
        """INSERT INTO consultas (combinacion_id, pagina, jobage_dias, ejecutada_en, resultado, n_resultados, codigo_error)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (combinacion_id, pagina, jobage_dias, ahora, resultado, n_resultados, codigo_error),
    )
    return cur.lastrowid


def fijar_nuevos(con: sqlite3.Connection, consulta_id: int, n_nuevos: int) -> None:
    con.execute("UPDATE consultas SET n_nuevos = ? WHERE consulta_id = ?", (n_nuevos, consulta_id))


def contar_desde(con: sqlite3.Connection, desde: str) -> int:
    """Recuento del día: se cuenta sobre el diario, no con un contador aparte que pueda desajustarse."""
    return con.execute("SELECT COUNT(*) FROM consultas WHERE ejecutada_en >= ?", (desde,)).fetchone()[0]


def ultimas(con: sqlite3.Connection, n: int) -> List[sqlite3.Row]:
    return con.execute("SELECT * FROM consultas ORDER BY consulta_id DESC LIMIT ?", (n,)).fetchall()


def hubo_resultados_alguna_vez(con: sqlite3.Connection) -> bool:
    return con.execute("SELECT 1 FROM consultas WHERE n_resultados > 0 LIMIT 1").fetchone() is not None


def registrar_hallazgo(con: sqlite3.Connection, job_id: str, consulta_id: int) -> None:
    con.execute("INSERT OR IGNORE INTO hallazgos (job_id, consulta_id) VALUES (?, ?)", (job_id, consulta_id))
