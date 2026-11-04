"""Consultas a Neon que usan la captura y los mensajes: una sola definición de «ofertas por revisar»."""
from __future__ import annotations

from typing import Callable, List, Optional

REVISAR_SQL = ("SELECT job_id, titulo, empresa, motivo_descarte, url FROM ofertas WHERE estado = 'revisar' "
               "ORDER BY fecha_hallazgo DESC;")


def ofertas_por_revisar(abrir: Optional[Callable]) -> Optional[List[dict]]:
    """Las ofertas por revisar, de Neon (ahí viven tus decisiones). None si no hay URL o Neon no responde."""
    if not abrir:
        return None
    try:
        pg = abrir()
        try:
            cur = pg.cursor()
            cur.execute(REVISAR_SQL)
            columnas = [c[0] for c in cur.description]
            return [dict(zip(columnas, fila)) for fila in cur.fetchall()]
        finally:
            pg.close()
    except Exception:
        return None
