"""Acceso a la tabla `ofertas` y a sus keywords."""
from __future__ import annotations

import sqlite3
from typing import Dict, Iterable, List, Optional

from collector.estados import DESCARTADA, PENDIENTE
from collector.util.texto import normalizar


def existe(con: sqlite3.Connection, job_id: str) -> bool:
    return con.execute("SELECT 1 FROM ofertas WHERE job_id = ?", (job_id,)).fetchone() is not None


def insertar_nueva(con: sqlite3.Connection, o: dict, ahora: str) -> bool:
    """True si la oferta era nueva."""
    cur = con.execute(
        """INSERT INTO ofertas (job_id, url, titulo, empresa, ubicacion, pais, fecha_publicacion,
               fecha_hallazgo, ultima_vista, modalidad, estado, motivo_descarte, huella, duplicada_de)
           VALUES (:job_id, :url, :titulo, :empresa, :ubicacion, :pais, :fecha_publicacion,
               :ahora, :ahora, :modalidad, :estado, :motivo_descarte, :huella, :duplicada_de)
           ON CONFLICT(job_id) DO NOTHING""",
        {**o, "ahora": ahora},
    )
    return cur.rowcount == 1


def buscar_original_por_huella(con: sqlite3.Connection, huella: str, job_id: str, desde: str) -> Optional[str]:
    """Otra oferta con la misma huella vista desde `desde` que no sea ella misma ni un duplicado."""
    fila = con.execute(
        """SELECT job_id FROM ofertas
           WHERE huella = ? AND job_id <> ? AND duplicada_de IS NULL AND fecha_hallazgo >= ?
           ORDER BY fecha_hallazgo LIMIT 1""",
        (huella, job_id, desde),
    ).fetchone()
    return fila["job_id"] if fila else None


def pendientes_de_detalle(con: sqlite3.Connection) -> List[sqlite3.Row]:
    """Ofertas aún sin detalle. El orden y cuáles se piden lo decide el prefiltro (`pipeline/seleccion.py`)."""
    return con.execute(
        """SELECT job_id, titulo, pais, motivo_descarte, fecha_publicacion, fecha_hallazgo FROM ofertas
           WHERE detalle_obtenido_en IS NULL AND estado = ?""", (PENDIENTE,)).fetchall()


def contar_detalles_desde(con: sqlite3.Connection, desde: str) -> int:
    return con.execute("SELECT COUNT(*) FROM ofertas WHERE detalle_obtenido_en >= ?", (desde,)).fetchone()[0]


def descartar(con: sqlite3.Connection, job_id: str, motivo: str, ahora: Optional[str] = None) -> None:
    """Descarta una oferta. Con `ahora` también cuenta como detalle consumido (p. ej. oferta cerrada)."""
    con.execute(
        "UPDATE ofertas SET estado = ?, motivo_descarte = ?, "
        "detalle_obtenido_en = COALESCE(?, detalle_obtenido_en) WHERE job_id = ?",
        (DESCARTADA, motivo, ahora, job_id),
    )


def guardar_evaluacion(con: sqlite3.Connection, job_id: str, d: dict, keywords: Iterable[str], ahora: str) -> None:
    con.execute(
        """UPDATE ofertas SET descripcion = :descripcion, detalle_obtenido_en = :ahora, tipo_empleo = :tipo_empleo,
               activa = :activa, modalidad_detectada = :modalidad_detectada, idioma_titulo = :idioma_titulo,
               idioma_contenido = :idioma_contenido, nivel_idioma = :nivel_idioma,
               estado = :estado, motivo_descarte = :motivo_descarte
           WHERE job_id = :job_id""",
        {**d, "job_id": job_id, "ahora": ahora},
    )
    con.execute("DELETE FROM oferta_keywords WHERE job_id = ?", (job_id,))
    con.executemany("INSERT OR IGNORE INTO oferta_keywords (job_id, keyword) VALUES (?, ?)",
                    [(job_id, k) for k in keywords])


def con_detalle_evaluable(con: sqlite3.Connection) -> List[sqlite3.Row]:
    """Aptas y por revisar con descripción guardada: las que una regla nueva puede cambiar sin pedir nada a LinkedIn."""
    return con.execute(
        """SELECT job_id, titulo, descripcion, activa, estado, motivo_descarte, modalidad_detectada FROM ofertas
           WHERE descripcion IS NOT NULL AND estado IN ('apta', 'revisar')""").fetchall()


def actualizar_evaluacion(con: sqlite3.Connection, job_id: str, d: dict) -> None:
    """Cambia solo el resultado de la evaluación; no toca la descripción ni cuándo se pidió el detalle."""
    con.execute(
        """UPDATE ofertas SET estado = :estado, motivo_descarte = :motivo_descarte,
               modalidad_detectada = :modalidad_detectada, idioma_titulo = :idioma_titulo,
               idioma_contenido = :idioma_contenido, nivel_idioma = :nivel_idioma
           WHERE job_id = :job_id""", {**d, "job_id": job_id})


def contar_por_estado(con: sqlite3.Connection) -> dict:
    return {f["estado"]: f["n"] for f in con.execute("SELECT estado, COUNT(*) AS n FROM ofertas GROUP BY estado")}


def buscar_original_por_contenido(con: sqlite3.Connection, empresa: Optional[str], descripcion: str, job_id: str,
                                  desde: str) -> Optional[str]:
    """La misma vacante publicada en otra ubicación: otra oferta de la misma empresa con la misma descripción (sin
    contar mayúsculas, acentos ni espacios), vista desde `desde`, que no sea un duplicado. La más antigua."""
    if not empresa or not (descripcion or "").strip():
        return None
    objetivo = normalizar(descripcion)
    filas = con.execute(
        """SELECT job_id, descripcion FROM ofertas
           WHERE empresa = ? AND job_id <> ? AND duplicada_de IS NULL AND descripcion IS NOT NULL AND fecha_hallazgo >= ?
           ORDER BY fecha_hallazgo, job_id""", (empresa, job_id, desde))
    return next((f["job_id"] for f in filas if normalizar(f["descripcion"]) == objetivo), None)


def marcar_duplicada(con: sqlite3.Connection, job_id: str, original: str) -> None:
    con.execute("UPDATE ofertas SET duplicada_de = ? WHERE job_id = ?", (original, job_id))


def grupos_por_contenido(con: sqlite3.Connection) -> List[List[sqlite3.Row]]:
    """Grupos de ofertas con la misma empresa y la misma descripción, la más antigua primero (la que se conserva)."""
    grupos: Dict[tuple, List[sqlite3.Row]] = {}
    for f in con.execute("""SELECT job_id, empresa, titulo, ubicacion, estado, descripcion FROM ofertas
                            WHERE descripcion IS NOT NULL AND empresa IS NOT NULL AND duplicada_de IS NULL
                            ORDER BY fecha_hallazgo, job_id"""):
        grupos.setdefault((f["empresa"], normalizar(f["descripcion"])), []).append(f)
    return [g for g in grupos.values() if len(g) > 1]


def borrar_copias(con: sqlite3.Connection, original: str, copias: List[str]) -> None:
    """Borra las copias con sus keywords y hallazgos; lo que apuntaba a ellas pasa a apuntar a la original.
    Los disparadores de la cola llevan el borrado a Neon (allí cae también su CV a medida, en cascada)."""
    huecos = ", ".join("?" * len(copias))
    con.execute(f"UPDATE ofertas SET duplicada_de = ? WHERE duplicada_de IN ({huecos})", (original, *copias))
    for tabla in ("oferta_keywords", "hallazgos", "ofertas"):
        con.execute(f"DELETE FROM {tabla} WHERE job_id IN ({huecos})", copias)
