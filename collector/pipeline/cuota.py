"""Recuento de las peticiones a LinkedIn de hoy (informativo: no hay tope diario). Se calcula contando filas, sin contadores."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Dict

from collector.db import consultas_repo, eventos_repo, ofertas_repo
from collector.util.reloj import a_iso, inicio_dia_local


def usadas_hoy(con: sqlite3.Connection, ahora: datetime) -> Dict[str, int]:
    """Peticiones de hoy por origen. Un detalle que falló o dio 429 también gastó una petición."""
    hoy = a_iso(inicio_dia_local(ahora))
    detalles = ofertas_repo.contar_detalles_desde(con, hoy) + eventos_repo.contar_detalles_fallidos(con, hoy)
    return {"busquedas": consultas_repo.contar_desde(con, hoy), "detalles": detalles}

