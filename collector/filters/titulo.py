"""Puntuación de un título de oferta por familias de raíces (inputs/prefiltro.md). Funciones puras.
Cada familia que aparece en el título suma su peso una sola vez; la suma decide si se pide el detalle."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Pattern, Tuple

from collector.config.modelos import ConfigPrefiltro, FamiliaTitulo
from collector.util.texto import normalizar

MOTIVO = "titulo_fuera_de_perfil"
SIN_FAMILIA = "sin_familia"
_PALABRA = re.compile(r"[a-z0-9&+#]+")


def _texto(titulo: str) -> str:
    """Minúsculas, sin acentos y solo palabras separadas por un espacio: «Analista (BI) / Datos» -> «analista bi datos»."""
    return " ".join(_PALABRA.findall(normalizar(titulo)))


def _patron(familia: FamiliaTitulo) -> Pattern[str]:
    partes = []
    for raiz in familia.raices:
        prefijo = raiz.endswith("*")
        partes.append(re.escape(_texto(raiz.rstrip("*"))) + ("" if prefijo else r"\b"))
    return re.compile(r"\b(?:" + "|".join(partes) + ")")


@dataclass(frozen=True)
class EvaluacionTitulo:
    puntos: int
    familias: Tuple[str, ...]          # las que aparecen, en el orden de la tabla
    negativa: str                      # la familia negativa de más peso, o '' si no hay


class FiltroTitulos:
    def __init__(self, cfg: ConfigPrefiltro):
        self._minimo = cfg.puntuacion_minima
        self._familias: List[Tuple[FamiliaTitulo, Pattern[str]]] = [(f, _patron(f)) for f in cfg.familias if f.raices]

    def evaluar(self, titulo: str) -> EvaluacionTitulo:
        texto = _texto(titulo)
        presentes = [f for f, p in self._familias if p.search(texto)]
        negativas = sorted((f for f in presentes if f.peso < 0), key=lambda f: f.peso)
        return EvaluacionTitulo(sum(f.peso for f in presentes), tuple(f.nombre for f in presentes),
                                negativas[0].nombre if negativas else "")

    def puntos(self, titulo: str) -> int:
        return self.evaluar(titulo).puntos

    def motivo_descarte(self, titulo: str) -> str:
        """'' si el título pasa; si no, «titulo_fuera_de_perfil:<familia negativa>» o «…:sin_familia»."""
        e = self.evaluar(titulo)
        return "" if e.puntos >= self._minimo else f"{MOTIVO}:{e.negativa or SIN_FAMILIA}"
