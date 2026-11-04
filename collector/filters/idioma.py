"""Idioma de un título o de una descripción, y nivel exigido del idioma vigilado. Funciones puras."""
from __future__ import annotations

import re
from typing import Optional, Tuple

from collector.config.modelos import ConfigIdioma
from collector.util.texto import alternativas, encontrar, hay_negacion_previa, normalizar

_PALABRA = re.compile(r"[a-z]+")


def _cuenta(texto: str, palabras) -> int:
    return sum(1 for p in _PALABRA.findall(normalizar(texto)) if p in palabras)


def idioma_de_texto(texto: str, cfg: ConfigIdioma) -> Optional[str]:
    """Código del idioma propio o del vigilado, 'mixto', o None si hay muy pocas palabras reconocibles."""
    propio, vigilado = _cuenta(texto, cfg.palabras[cfg.propio]), _cuenta(texto, cfg.palabras[cfg.vigilado])
    total = propio + vigilado
    if total < cfg.minimo_palabras:
        return None
    if propio / total >= cfg.umbral:
        return cfg.propio
    if vigilado / total >= cfg.umbral:
        return cfg.vigilado
    return "mixto"


def idioma_de_titulo(titulo: str, cfg: ConfigIdioma) -> Optional[str]:
    propio, vigilado = _cuenta(titulo, cfg.palabras_titulo[cfg.propio]), _cuenta(titulo, cfg.palabras_titulo[cfg.vigilado])
    if propio and vigilado:
        return "mixto"
    if propio:
        return cfg.propio
    return cfg.vigilado if vigilado else None


def _senal_rechazo(texto: str, expresion: str, cfg: ConfigIdioma) -> Optional[bool]:
    """None si no aparece; True si cuenta como rechazo; False si una negación la anula."""
    coincidencias = encontrar(texto, expresion)
    if not coincidencias:
        return None
    anulada = all(hay_negacion_previa(texto, m.start(), cfg.negaciones, cfg.ventana_negacion)
                  for m in coincidencias)
    return not anulada


def _senales_mcer(texto: str, cfg: ConfigIdioma) -> Tuple[bool, bool]:
    """(hay nivel aceptable, hay nivel exigente): cuentan solo junto a un alias del idioma vigilado."""
    acepta = rechaza = False
    alias = alternativas(cfg.alias_vigilado)
    for m in alternativas(cfg.mcer).finditer(texto):
        cerca = texto[max(0, m.start() - cfg.ventana_mcer):m.end() + cfg.ventana_mcer]
        if alias.search(cerca):
            acepta, rechaza = acepta or cfg.mcer[m.group(1)] == "pasa", rechaza or cfg.mcer[m.group(1)] != "pasa"
    return acepta, rechaza


def nivel_idioma(descripcion: str, cfg: ConfigIdioma) -> str:
    """'ninguno' | 'aceptable' | 'exigente' | 'dudoso' (señales de ambos lados)."""
    t = normalizar(descripcion)
    acepta = any(encontrar(t, e) for e in cfg.pasa)
    rechaza = False
    for e in cfg.rechaza:
        senal = _senal_rechazo(t, e, cfg)
        rechaza = rechaza or senal is True
        acepta = acepta or senal is False
    mcer_acepta, mcer_rechaza = _senales_mcer(t, cfg)
    acepta, rechaza = acepta or mcer_acepta, rechaza or mcer_rechaza
    if acepta and rechaza:
        return "dudoso"
    return "exigente" if rechaza else "aceptable" if acepta else "ninguno"
