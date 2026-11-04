"""Decisión sobre una oferta con su detalle: aplica las reglas de inputs/decisiones.md. Funciones puras.

El vocabulario de condiciones es del sistema; el estado y el motivo de cada regla los fija el usuario.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Sequence, Tuple

from collector.config.modelos import ReglaDecision
from collector.estados import CONDICIONES


@dataclass
class Contexto:
    activa: bool
    modalidad_fuera: Optional[str]      # modalidad de la oferta si LinkedIn la rotula y no es la aceptada
    nivel: str                          # ninguno | aceptable | exigente | dudoso
    idioma_titulo: Optional[str]
    idioma_contenido: Optional[str]
    pais_desconocido: bool
    vigilado: str                       # código del idioma vigilado


EVALUADORES: Dict[str, Callable[[Contexto], bool]] = {
    "cerrada": lambda c: not c.activa,
    "detalle_ilegible": lambda c: False,   # se aplica antes de evaluar, en pipeline/detail_runner.py
    "modalidad_no_aceptada": lambda c: bool(c.modalidad_fuera),
    "nivel_exigente": lambda c: c.nivel == "exigente",
    "nivel_dudoso": lambda c: c.nivel == "dudoso",
    "contenido_vigilado_titulo_no": lambda c: c.idioma_contenido == c.vigilado and c.idioma_titulo != c.vigilado,
    "contenido_vigilado_nivel_aceptable": lambda c: c.idioma_contenido == c.vigilado and c.nivel == "aceptable",
    "contenido_vigilado": lambda c: c.idioma_contenido == c.vigilado,
    "pais_desconocido": lambda c: c.pais_desconocido,
    "siempre": lambda c: True,
}

assert tuple(EVALUADORES) == CONDICIONES, "estados.CONDICIONES y filters/decision.py deben listar lo mismo"


def decidir(ctx: Contexto, reglas: Sequence[ReglaDecision]) -> Tuple[str, Optional[str]]:
    """(estado, motivo) de la primera regla que se cumple. La carga de inputs garantiza que la última es «siempre»."""
    for r in reglas:
        if EVALUADORES[r.condicion](ctx):
            motivo = r.motivo.format(modalidad=ctx.modalidad_fuera) if r.motivo else None
            return r.estado, motivo
    raise ValueError("reglas de decisión sin la regla final «siempre»")
