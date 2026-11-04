"""Reevaluar con las reglas actuales (inputs/) las ofertas aptas o por revisar que ya tienen descripción.
No pide nada a LinkedIn: sirve cuando cambian decisiones.md, modalidades.md o idioma.md."""
from __future__ import annotations

import sqlite3
from collections import Counter
from typing import Dict, Tuple

from collector.config.modelos import Config
from collector.db import ofertas_repo
from collector.filters.evaluar import evaluar

Cambio = Tuple[str, str]   # (antes, después), cada uno «estado» o «estado:motivo»


def _etiqueta(estado: str, motivo) -> str:
    return f"{estado}:{motivo}" if motivo else estado


def reevaluar(con: sqlite3.Connection, cfg: Config, aplicar: bool) -> Dict[Cambio, int]:
    """Cuenta los cambios (antes, después). Con `aplicar` los guarda; sin él, solo informa."""
    marca_pais = cfg.decisiones.ingreso["pais_desconocido"].motivo_para(None, "")
    cambios: Counter = Counter()
    for o in ofertas_repo.con_detalle_evaluable(con):
        ev = evaluar(o["titulo"], o["descripcion"], bool(o["activa"] if o["activa"] is not None else 1), cfg,
                     o["motivo_descarte"] == marca_pais, o["modalidad_detectada"])
        antes, despues = _etiqueta(o["estado"], o["motivo_descarte"]), _etiqueta(ev.estado, ev.motivo_descarte)
        if antes == despues:
            continue
        cambios[(antes, despues)] += 1
        if aplicar:
            ofertas_repo.actualizar_evaluacion(con, o["job_id"], {
                "estado": ev.estado, "motivo_descarte": ev.motivo_descarte, "modalidad_detectada": ev.modalidad_detectada,
                "idioma_titulo": ev.idioma_titulo, "idioma_contenido": ev.idioma_contenido, "nivel_idioma": ev.nivel_idioma})
    return dict(cambios)
