"""Selección de las ofertas a las que se les pide el detalle. Sin red ni escritura: solo decide y ordena."""
from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

from collector.config.modelos import Config
from collector.filters.titulo import FiltroTitulos

ESPERA_PAIS = "pais_sin_confirmar"


@dataclass
class Elegible:
    oferta: sqlite3.Row
    puntos: int
    prioridad_pais: int


@dataclass
class Seleccion:
    elegibles: List[Elegible] = field(default_factory=list)   # ya ordenadas; recortadas al límite pedido
    total_elegibles: int = 0
    en_espera: Dict[str, int] = field(default_factory=dict)   # motivo -> cuántas


_CLAVES: Dict[str, Callable[[Elegible], object]] = {
    "prioridad_pais": lambda e: e.prioridad_pais,
    "puntos": lambda e: e.puntos,
    "recencia": lambda e: (e.oferta["fecha_publicacion"] or "", e.oferta["fecha_hallazgo"]),
}


def seleccionar(pendientes: Sequence[sqlite3.Row], cfg: Config, limite: Optional[int] = None) -> Seleccion:
    """Elegible = país confirmado (salvo que la regla de ingreso `pais_desconocido` sea «evaluar») y título que
    alcanza `puntuacion_minima`. Un título que no la alcanza ya se descarta al entrar (ingest), así que aquí solo
    se salta por si acaso. El orden lo fija la tabla «Orden del detalle» de prefiltro.md."""
    pf = cfg.prefiltro
    regla_pais = cfg.decisiones.ingreso["pais_desconocido"]
    filtro = FiltroTitulos(pf)
    elegibles: List[Elegible] = []
    espera: Counter = Counter()
    for o in pendientes:
        if regla_pais.accion == "esperar" and o["motivo_descarte"] == regla_pais.motivo_para(None, ""):
            espera[ESPERA_PAIS] += 1
            continue
        puntos = filtro.puntos(o["titulo"])
        if puntos < pf.puntuacion_minima:
            continue
        elegibles.append(Elegible(o, puntos, pf.prioridad_pais.get(o["pais"], pf.prioridad_pais_defecto)))
    for criterio, sentido in reversed(pf.orden):   # orden estable: el último criterio se aplica primero
        elegibles.sort(key=_CLAVES[criterio], reverse=sentido == "desc")
    return Seleccion(elegibles if limite is None else elegibles[:max(0, limite)], len(elegibles), dict(espera))
