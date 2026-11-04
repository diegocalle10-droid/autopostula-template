"""Lee las tablas markdown de inputs/*.md: {clave_de_seccion: [fila, ...]}."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Dict, List


def clave(texto: str) -> str:
    """'Países aceptados' -> 'paises_aceptados'."""
    s = unicodedata.normalize("NFD", texto.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _celdas(linea: str) -> List[str]:
    return [p.strip() for p in linea.strip().strip("|").split("|")]


def _es_separador(celdas: List[str]) -> bool:
    return any(celdas) and all(re.fullmatch(r":?-{3,}:?", c) for c in celdas if c)


def leer_tablas(ruta) -> Dict[str, List[Dict[str, str]]]:
    """Cada tabla se asocia al último encabezado (#, ##, ###) que la precede."""
    tablas: Dict[str, List[Dict[str, str]]] = {}
    seccion = ""
    cabecera = None
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        if linea.startswith("#"):
            seccion, cabecera = clave(linea.lstrip("#")), None
            continue
        if not linea.lstrip().startswith("|"):
            cabecera = None
            continue
        celdas = _celdas(linea)
        if cabecera is None:
            cabecera = [clave(c) for c in celdas]
            continue
        if _es_separador(celdas) or len(celdas) != len(cabecera):
            continue
        tablas.setdefault(seccion, []).append(dict(zip(cabecera, celdas)))
    return tablas
