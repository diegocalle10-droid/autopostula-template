"""Construye la agenda de búsquedas: cada término × cada ubicación válida."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import List

from collector.config.modelos import Config
from collector.db import combinaciones_repo
from collector.db.combinaciones_repo import Deseada
from collector.util.reloj import a_iso


def combinaciones_deseadas(cfg: Config) -> List[Deseada]:
    return [(t.termino, u.frase, t.prioridad, cfg.cadencia(t.prioridad))
            for t in cfg.terminos for u in cfg.ubicaciones]


def sincronizar(con: sqlite3.Connection, cfg: Config, ahora: datetime) -> dict:
    """Alinea `combinaciones` con inputs/. Lo nuevo queda pendiente de ejecutar desde ya."""
    return combinaciones_repo.sincronizar(con, combinaciones_deseadas(cfg), a_iso(ahora))
