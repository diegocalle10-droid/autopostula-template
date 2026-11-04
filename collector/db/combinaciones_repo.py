"""Acceso a `combinaciones`: la agenda de búsquedas (qué toca buscar y cuándo)."""
from __future__ import annotations

import sqlite3
from typing import Iterable, List, Tuple

Deseada = Tuple[str, str, int, int]   # (termino, ubicacion_frase, prioridad, cadencia_dias)
_DEBIDA = "activa = 1 AND (proxima_ejecucion IS NULL OR proxima_ejecucion <= ?)"


def sincronizar(con: sqlite3.Connection, deseadas: Iterable[Deseada], ahora: str) -> dict:
    """Alinea la tabla con inputs/. No pisa la cadencia ya podada de las que existen."""
    deseadas = list(deseadas)
    claves = {(t, u) for t, u, _, _ in deseadas}
    antes = con.execute("SELECT COUNT(*) FROM combinaciones").fetchone()[0]
    for termino, ubic, prioridad, cadencia in deseadas:
        con.execute(
            """INSERT INTO combinaciones (termino, ubicacion_frase, prioridad, cadencia_dias, proxima_ejecucion)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(termino, ubicacion_frase) DO UPDATE SET prioridad = excluded.prioridad, activa = 1,
                   cadencia_dias = CASE WHEN prioridad <> excluded.prioridad THEN excluded.cadencia_dias ELSE cadencia_dias END,
                   proxima_ejecucion = CASE WHEN prioridad <> excluded.prioridad THEN excluded.proxima_ejecucion
                                            ELSE proxima_ejecucion END
               WHERE prioridad <> excluded.prioridad OR activa = 0""",   # sin cambios no se toca (ni se resube a Neon)
            (termino, ubic, prioridad, cadencia, ahora),
        )
    despues = con.execute("SELECT COUNT(*) FROM combinaciones").fetchone()[0]
    retiradas = 0
    for fila in con.execute("SELECT combinacion_id, termino, ubicacion_frase FROM combinaciones WHERE activa = 1").fetchall():
        if (fila["termino"], fila["ubicacion_frase"]) not in claves:
            retirar(con, fila["combinacion_id"])
            retiradas += 1
    return {"total": len(deseadas), "nuevas": despues - antes, "retiradas": retiradas}


def retirar(con: sqlite3.Connection, combinacion_id: int) -> None:
    con.execute("UPDATE combinaciones SET activa = 0 WHERE combinacion_id = ?", (combinacion_id,))


def contar(con: sqlite3.Connection) -> dict:
    f = con.execute("SELECT COUNT(*) AS t, COALESCE(SUM(activa), 0) AS a FROM combinaciones").fetchone()
    return {"total": f["t"], "activas": f["a"]}


def debidas(con: sqlite3.Connection, ahora: str, limite: int) -> List[sqlite3.Row]:
    return con.execute(
        f"""SELECT * FROM combinaciones WHERE {_DEBIDA}
           ORDER BY prioridad, COALESCE(proxima_ejecucion, ''), combinacion_id LIMIT ?""",
        (ahora, limite),
    ).fetchall()


def contar_debidas(con: sqlite3.Connection, ahora: str) -> int:
    return con.execute(
        f"SELECT COUNT(*) FROM combinaciones WHERE {_DEBIDA}",
        (ahora,),
    ).fetchone()[0]


def cerrar(con: sqlite3.Connection, combinacion_id: int, ahora: str, proxima: str, hubo_nuevas: bool) -> None:
    """Fin de una pasada correcta: fija la próxima y cuenta las pasadas seguidas sin ofertas nuevas."""
    con.execute(
        """UPDATE combinaciones SET ultima_ejecucion = ?, proxima_ejecucion = ?,
               pasadas_sin_nuevas = CASE WHEN ? THEN 0 ELSE pasadas_sin_nuevas + 1 END
           WHERE combinacion_id = ?""",
        (ahora, proxima, 1 if hubo_nuevas else 0, combinacion_id),
    )


def reprogramar(con: sqlite3.Connection, combinacion_id: int, proxima: str) -> None:
    """Tras un fallo: se reintenta más tarde sin dar la pasada por hecha."""
    con.execute("UPDATE combinaciones SET proxima_ejecucion = ? WHERE combinacion_id = ?", (proxima, combinacion_id))


def fijar_cadencia(con: sqlite3.Connection, combinacion_id: int, dias: int, reiniciar_contador: bool = False) -> None:
    con.execute(
        "UPDATE combinaciones SET cadencia_dias = ?, pasadas_sin_nuevas = CASE WHEN ? THEN 0 ELSE pasadas_sin_nuevas END "
        "WHERE combinacion_id = ?",
        (dias, 1 if reiniciar_contador else 0, combinacion_id),
    )


def ubicaciones_sin_resultados(con: sqlite3.Connection, minimo_terminos: int, prioridad_maxima: int) -> List[sqlite3.Row]:
    """Ubicaciones sin una sola consulta con datos, probadas con al menos `minimo_terminos` términos distintos."""
    return con.execute(
        """SELECT c.ubicacion_frase FROM combinaciones c
           JOIN consultas q ON q.combinacion_id = c.combinacion_id AND q.resultado IN ('ok','vacia')
           WHERE c.prioridad <= ?
           GROUP BY c.ubicacion_frase
           HAVING COUNT(DISTINCT c.termino) >= ? AND SUM(CASE WHEN q.n_resultados > 0 THEN 1 ELSE 0 END) = 0""",
        (prioridad_maxima, minimo_terminos),
    ).fetchall()


def espaciar_ubicacion(con: sqlite3.Connection, ubicacion_frase: str, cadencia_dias: int) -> int:
    """Sube a `cadencia_dias` la cadencia de todas las combinaciones de la ubicación. Devuelve cuántas cambiaron."""
    return con.execute("UPDATE combinaciones SET cadencia_dias = ? WHERE ubicacion_frase = ? AND cadencia_dias < ?",
                       (cadencia_dias, ubicacion_frase, cadencia_dias)).rowcount


def con_pasadas_sin_nuevas(con: sqlite3.Connection, minimo: int) -> List[sqlite3.Row]:
    return con.execute("SELECT * FROM combinaciones WHERE activa = 1 AND pasadas_sin_nuevas >= ?", (minimo,)).fetchall()


def que_vuelven_a_aportar(con: sqlite3.Connection) -> List[sqlite3.Row]:
    """Combinaciones cuya última búsqueda correcta trajo ofertas nuevas."""
    return con.execute(
        """SELECT c.* FROM combinaciones c
           WHERE c.activa = 1 AND c.ultima_ejecucion IS NOT NULL
             AND (SELECT q.n_nuevos FROM consultas q
                  WHERE q.combinacion_id = c.combinacion_id AND q.resultado = 'ok'
                  ORDER BY q.consulta_id DESC LIMIT 1) > 0"""
    ).fetchall()
