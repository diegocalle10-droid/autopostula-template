#!/usr/bin/env python3
"""Falla si algún archivo supera 300 líneas o alguna función supera 40. Avisa desde 250 líneas."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
OBJETIVO, TOPE_ARCHIVO, TOPE_FUNCION = 250, 300, 40
EXCLUIR = {"data", "logs", "__pycache__", ".git"}
# Archivos que superan el objetivo (no el tope) por una razón fundada: no avisan. El tope de 300 sigue valiendo.
EXENTOS_DEL_AVISO = {"collector/config/cargar.py": "valida cada archivo de inputs/ y solo puede crecer con ellos"}


def archivos():
    for ruta in sorted(RAIZ.rglob("*.py")):
        if not (set(ruta.relative_to(RAIZ).parts) & EXCLUIR):
            yield ruta


def funciones_largas(ruta: Path):
    arbol = ast.parse(ruta.read_text(encoding="utf-8-sig"))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            largo = nodo.end_lineno - nodo.lineno + 1
            if largo > TOPE_FUNCION:
                yield nodo.name, nodo.lineno, largo


def main() -> int:
    errores, avisos, total = [], [], 0
    for ruta in archivos():
        total += 1
        rel = ruta.relative_to(RAIZ)
        n = len(ruta.read_text(encoding="utf-8").splitlines())
        if n > TOPE_ARCHIVO:
            errores.append(f"{rel}: {n} líneas (tope {TOPE_ARCHIVO})")
        elif n > OBJETIVO and rel.as_posix() not in EXENTOS_DEL_AVISO:
            avisos.append(f"{rel}: {n} líneas (objetivo {OBJETIVO})")
        for nombre, linea, largo in funciones_largas(ruta):
            errores.append(f"{rel}:{linea} función «{nombre}» de {largo} líneas (tope {TOPE_FUNCION})")
    for a in avisos:
        print("AVISO ", a)
    for e in errores:
        print("ERROR ", e)
    print(f"{total} archivos revisados: {len(errores)} errores, {len(avisos)} avisos.")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
