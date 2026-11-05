"""Escribe el geo_id de una ubicación en su fila de inputs/ubicaciones.md, sin tocar el resto del archivo."""
from __future__ import annotations

from typing import List


def _celdas(linea: str) -> List[str]:
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def fijar_geo_id(texto: str, frase: str, geo_id: str) -> str:
    """Devuelve `texto` con el geo_id de la fila de `frase` (tablas con columna geo_id). Error si la fila no existe."""
    lineas = texto.split("\n")
    columna = None
    for i, linea in enumerate(lineas):
        if not linea.lstrip().startswith("|"):
            columna = None
            continue
        celdas = _celdas(linea)
        if "geo_id" in celdas and "frase" in celdas:
            columna, col_frase = celdas.index("geo_id"), celdas.index("frase")
        elif columna is not None and len(celdas) > columna and celdas[col_frase] == frase:
            celdas[columna] = geo_id
            lineas[i] = "| " + " | ".join(celdas) + " |"
            return "\n".join(lineas)
    raise ValueError(f"ubicaciones.md: no hay ninguna fila con la frase «{frase}» en una tabla con columna geo_id")
