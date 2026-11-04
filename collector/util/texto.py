"""Normalización y búsqueda de expresiones en texto. Funciones puras."""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, List

_ESPACIOS = re.compile(r"\s+")
_DELIMITADOR = re.compile(r"[.;:!?]")
_CACHE: Dict[str, "re.Pattern[str]"] = {}


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos, espacios colapsados. Un salto de línea cuenta como fin de frase."""
    s = unicodedata.normalize("NFD", (texto or "").lower().replace("\n", ". "))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return _ESPACIOS.sub(" ", s).strip()


def patron(expresion: str) -> "re.Pattern[str]":
    """'re:...' es una expresión regular; el resto, texto literal con límites de palabra."""
    p = _CACHE.get(expresion)
    if p is None:
        if expresion.startswith("re:"):
            p = re.compile(expresion[3:], re.IGNORECASE)
        else:
            p = re.compile(r"(?<!\w)" + re.escape(normalizar(expresion)) + r"(?!\w)")
        _CACHE[expresion] = p
    return p


def alternativas(expresiones: Iterable[str]) -> "re.Pattern[str]":
    """Reconoce cualquiera de las expresiones literales como palabra completa; la más larga primero."""
    ordenadas = sorted({normalizar(e) for e in expresiones}, key=len, reverse=True)
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(e) for e in ordenadas) + r")(?!\w)")


def encontrar(texto_norm: str, expresion: str) -> List["re.Match[str]"]:
    return list(patron(expresion).finditer(texto_norm))


def ventana_previa(texto_norm: str, inicio: int, caracteres: int) -> str:
    """Hasta `caracteres` antes de `inicio`, cortada en el último fin de frase."""
    trozo = texto_norm[max(0, inicio - caracteres):inicio]
    cortes = list(_DELIMITADOR.finditer(trozo))
    return trozo[cortes[-1].end():] if cortes else trozo


def hay_negacion_previa(texto_norm: str, inicio: int, negaciones: Iterable[str], caracteres: int) -> bool:
    ventana = ventana_previa(texto_norm, inicio, caracteres)
    return any(patron(n).search(ventana) for n in negaciones)
