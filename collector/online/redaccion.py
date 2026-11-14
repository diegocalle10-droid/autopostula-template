"""Antes de validar un CV de la rutina (runbook v7): componer `cv_md` desde `contenido`, comprobar que todas sus
keywords están en las viñetas de experiencia y recalcular la afinidad con la evidencia real del CV base. Sin IA.

Una fila sin `keywords` ni `contenido` es del flujo anterior: se valida su `cv_md` como siempre."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from collector.cv.componer import componer
from collector.filters.cv_cobertura import afinidad, errores_keywords, faltantes

PLANTILLA = Path("CV") / "plantilla.md"


@dataclass
class Preparado:
    cv_md: str
    errores: List[str] = field(default_factory=list)
    afinidad: Optional[int] = None          # recalculada; None en el flujo anterior
    cubiertos: str = ""
    sin_respaldo: str = ""


def cargar_json(valor):
    """Neon devuelve JSONB ya convertido; la SQLite de las pruebas, texto."""
    if isinstance(valor, (str, bytes)):
        try:
            return json.loads(valor)
        except ValueError:
            return valor
    return valor


def _cobertura(cfg, keywords: list, cv_md: str) -> List[str]:
    falta = faltantes(keywords, cv_md)
    cobertura = round(100 * (len(keywords) - len(falta)) / len(keywords))
    if cobertura >= cfg.cv.cobertura_minima:
        return []
    return [f"faltan en las viñetas de experiencia {len(falta)} keywords (cobertura {cobertura} %, mínimo "
            f"{cfg.cv.cobertura_minima} %): {', '.join(falta)}. Redacta cada una como función dentro del puesto donde "
            f"sea más verosímil, con la misma `kw` o una de sus `variantes`"]


def preparar(cfg, raiz: Path, o: dict, base_md: str) -> Preparado:
    contenido, keywords = cargar_json(o.get("contenido")), cargar_json(o.get("keywords"))
    if contenido is None and keywords is None:
        return Preparado(o.get("cv_md") or "")
    errores = errores_keywords(keywords, cfg.cv.keywords_min, cfg.cv.keywords_max)
    cv_md = o.get("cv_md") or ""
    if contenido is not None:
        cv_md, fallos = componer((Path(raiz) / PLANTILLA).read_text(encoding="utf-8"), base_md, contenido)
        errores += fallos
    if errores:
        return Preparado(cv_md, errores)
    af, cubiertos, sin_respaldo = afinidad(keywords, base_md)
    return Preparado(cv_md, _cobertura(cfg, keywords, cv_md), af, cubiertos, sin_respaldo)
