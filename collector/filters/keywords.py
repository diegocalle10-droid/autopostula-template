"""Palabras clave de una oferta: los términos de inputs/puestos.md que aparecen en su descripción."""
from __future__ import annotations

from typing import Iterable, List

from collector.util.texto import encontrar, normalizar


def keywords_en(descripcion: str, terminos: Iterable[str]) -> List[str]:
    t = normalizar(descripcion)
    return [x for x in dict.fromkeys(terminos) if encontrar(t, x)]
