"""Keywords de una oferta frente al CV generado y al CV base. Funciones puras, sin IA.

Cada keyword es un objeto {kw, variantes, tipo, respaldo, evidencia}: `kw` es el término tal como lo escribe el anuncio
y `variantes` sus otras formas (sigla, nombre corto). Cuenta como cubierta si `kw` o una variante aparece, como
palabra completa, en alguna viñeta de la sección de experiencia."""
from __future__ import annotations

from typing import Iterable, List, Tuple

from collector.util.texto import normalizar, patron

RESPALDOS = ("directo", "parcial", "ninguno")


def vinetas_experiencia(cv_md: str) -> str:
    """Texto normalizado de las viñetas de la sección de experiencia (no cuentan perfil, stack ni títulos)."""
    seccion, lineas = "", []
    for linea in cv_md.splitlines():
        s = linea.strip()
        if s.startswith("## "):
            seccion = normalizar(s[3:])
        elif seccion.startswith("experiencia") and s.startswith("- "):
            lineas.append(s[2:])
    return normalizar("\n".join(lineas))


def _terminos(k: dict) -> List[str]:
    """`kw` y sus variantes como texto literal (un «re:» inicial no se toma por expresión regular)."""
    crudos = [k.get("kw")] + list(k.get("variantes") or [])
    return [str(t).strip().removeprefix("re:") for t in crudos if t and str(t).strip()]


def faltantes(keywords: Iterable[dict], cv_md: str) -> List[str]:
    texto = vinetas_experiencia(cv_md)
    return [str(k.get("kw")) for k in keywords if not any(patron(t).search(texto) for t in _terminos(k))]


def errores_keywords(keywords, minimo: int, maximo: int) -> List[str]:
    if not isinstance(keywords, list) or not all(isinstance(k, dict) and str(k.get("kw") or "").strip() for k in keywords):
        return ["`keywords` debe ser una lista de objetos con `kw`"]
    if not minimo <= len(keywords) <= maximo:
        return [f"hay {len(keywords)} keywords y deben ser entre {minimo} y {maximo}"]
    return []


def respaldo_efectivo(k: dict, base_md: str) -> str:
    """El respaldo declarado, salvo que su `evidencia` no sea texto del CV base: entonces cuenta como «ninguno»."""
    declarado = k.get("respaldo") if k.get("respaldo") in RESPALDOS else "ninguno"
    evidencia = normalizar(str(k.get("evidencia") or "")).strip(" .")
    if declarado == "ninguno" or not evidencia or evidencia not in normalizar(base_md):
        return "ninguno"
    return declarado


def afinidad(keywords: List[dict], base_md: str) -> Tuple[int, str, str]:
    """(afinidad %, cubiertas, no cubiertas) con la fórmula del runbook y solo con evidencia real del CV base."""
    respaldos = [(str(k["kw"]), respaldo_efectivo(k, base_md)) for k in keywords]
    puntos = sum(1 if r == "directo" else 0.5 if r == "parcial" else 0 for _, r in respaldos)
    cubiertas = ", ".join(kw for kw, r in respaldos if r != "ninguno")
    sin_respaldo = ", ".join(kw for kw, r in respaldos if r == "ninguno")
    return (round(100 * puntos / len(respaldos)) if respaldos else 0), cubiertas, sin_respaldo
