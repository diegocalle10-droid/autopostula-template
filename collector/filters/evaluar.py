"""Evaluación de una oferta con su detalle: idioma, nivel exigido, modalidad (la etiqueta de LinkedIn), keywords y decisión."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from collector.config.modelos import Config
from collector.filters.decision import Contexto, decidir
from collector.filters.idioma import idioma_de_texto, idioma_de_titulo, nivel_idioma
from collector.filters.keywords import keywords_en


@dataclass
class Evaluacion:
    estado: str
    motivo_descarte: Optional[str]
    idioma_titulo: Optional[str]
    idioma_contenido: Optional[str]
    nivel_idioma: str
    modalidad_detectada: Optional[str]
    keywords: List[str] = field(default_factory=list)


def evaluar(titulo: str, descripcion: str, activa: bool, cfg: Config, pais_desconocido: bool = False,
            modalidad: Optional[str] = None) -> Evaluacion:
    it = idioma_de_titulo(titulo, cfg.idioma)
    ic = idioma_de_texto(descripcion, cfg.idioma)
    nivel = nivel_idioma(descripcion, cfg.idioma)
    fuera = modalidad if modalidad and modalidad not in cfg.modalidad.aceptadas else None
    contexto = Contexto(activa, fuera, nivel, it, ic, pais_desconocido, cfg.idioma.vigilado)
    estado, motivo = decidir(contexto, cfg.decisiones.reglas)
    kws = keywords_en(descripcion, (t.termino for t in cfg.terminos))
    return Evaluacion(estado, motivo, it, ic, nivel, modalidad, kws)
