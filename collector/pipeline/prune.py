"""Poda por rendimiento: espacia lo que no aporta y recupera lo que vuelve a aportar.

Nada se excluye por prioridad geográfica, solo por falta de resultados medida.
"""
from __future__ import annotations

import sqlite3

from collector.config.modelos import Config
from collector.db import combinaciones_repo


def podar(con: sqlite3.Connection, cfg: Config) -> dict:
    lotes = cfg.lotes
    maximo = lotes.entero("cadencia_maxima_dias")
    resumen = {"ubicaciones_espaciadas": 0, "cadencias_duplicadas": 0, "recuperadas": 0}

    sin_datos = combinaciones_repo.ubicaciones_sin_resultados(
        con, lotes.entero("ubicacion_sin_resultados_terminos"), lotes.entero("ubicacion_sin_resultados_prioridad_max"))
    for fila in sin_datos:
        cambiadas = combinaciones_repo.espaciar_ubicacion(con, fila["ubicacion_frase"], maximo)
        resumen["ubicaciones_espaciadas"] += 1 if cambiadas else 0

    for c in combinaciones_repo.con_pasadas_sin_nuevas(con, lotes.entero("pasadas_sin_nuevas_para_duplicar")):
        nueva = min(c["cadencia_dias"] * lotes.entero("factor_cadencia_poda"), maximo)
        if nueva > c["cadencia_dias"]:
            combinaciones_repo.fijar_cadencia(con, c["combinacion_id"], nueva, reiniciar_contador=True)
            resumen["cadencias_duplicadas"] += 1

    for c in combinaciones_repo.que_vuelven_a_aportar(con):
        base = cfg.cadencia(c["prioridad"])
        if c["cadencia_dias"] > base:
            combinaciones_repo.fijar_cadencia(con, c["combinacion_id"], base)
            resumen["recuperadas"] += 1
    return resumen
