"""Búsquedas de control: distinguen el fallo de unas combinaciones (una página rara, un mercado sin ofertas) del fallo de
todo el sistema (LinkedIn cambió la página, la sesión caducó, un bloqueo blando).

Cuando las últimas `sospechas_para_control` combinaciones seguidas fallan, se repiten hasta `busquedas_de_control`
búsquedas que hace poco sí trajeron ofertas. Si alguna trae lista, el sistema funciona y la captura sigue; si ninguna,
se para sin plazo y se avisa. La siguiente captura empieza con una búsqueda de control: si trae lista, levanta la parada
sola. Un vacío que confirma LinkedIn («no hay resultados») no es un fallo y no cuenta."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Callable, List, Optional, Tuple

from collector.config.modelos import Config
from collector.db import consultas_repo, eventos_repo
from collector.db.connection import transaccion
from collector.linkedin.errores import LimiteError, LinkedinError
from collector.pipeline import breaker
from collector.util.reloj import a_iso

# Pide la página 1 de una combinación, la registra y devuelve cuántas tarjetas trajo; LinkedinError si falla.
Pedir = Callable[[sqlite3.Row], int]


def combinaciones_en_racha(con: sqlite3.Connection) -> List[int]:
    """Combinaciones distintas de la racha de consultas fallidas con la que acaba el diario."""
    vistas: List[int] = []
    for c in consultas_repo.racha_fallida(con):
        if c["combinacion_id"] not in vistas:
            vistas.append(c["combinacion_id"])
    return vistas


def probar(con: sqlite3.Connection, cfg: Config, pedir: Pedir, excluir: List[int], n: int) -> Tuple[bool, int]:
    """Hasta `n` búsquedas de control con las combinaciones que más recientemente trajeron ofertas.
    (True en cuanto una trae lista, peticiones hechas). Un 429 sube tal cual: nunca se reintenta."""
    peticiones = 0
    candidatas = [c for c in consultas_repo.combinaciones_de_control(con, excluir, n * 3)
                  if cfg.ubicacion_por_frase(c["ubicacion_frase"])]
    for combo in candidatas[:n]:
        peticiones += 1
        try:
            if pedir(combo) > 0:
                return True, peticiones
        except LimiteError:
            raise
        except LinkedinError:
            continue
    return False, peticiones


def revisar(con: sqlite3.Connection, cfg: Config, pedir: Pedir, ahora: datetime) -> Tuple[Optional[str], int]:
    """Tras cada combinación. (motivo de la parada o None si se sigue, peticiones de control hechas)."""
    racha = combinaciones_en_racha(con)
    if len(racha) < cfg.lotes.entero("sospechas_para_control"):
        return None, 0
    ok, n = probar(con, cfg, pedir, racha, cfg.lotes.entero("busquedas_de_control"))
    if ok:
        return None, n
    motivo = f"{len(racha)} combinaciones seguidas fallaron y {n} búsquedas de control tampoco trajeron lista"
    with transaccion(con):
        breaker.parar_por_sospecha(con, ahora, motivo)
    return motivo, n


def comprobar_al_arrancar(con: sqlite3.Connection, cfg: Config, pedir: Pedir, ahora: datetime) -> Tuple[Optional[str], int]:
    """Con una parada por sospecha vigente, una búsqueda de control: si trae lista, la parada se levanta sola (None);
    si no, sigue y se devuelve el motivo para avisar otra vez."""
    parada = breaker.hay_parada_por_sospecha(con, ahora)
    if not parada:
        return None, 0
    ok, n = probar(con, cfg, pedir, [], 1)
    if ok:
        with transaccion(con):
            eventos_repo.cancelar_pausa_con(con, a_iso(ahora), breaker.MARCA_SOSPECHA)
        return None, n
    return f"sigue parada: la búsqueda de control tampoco trajo lista ({parada['contexto']})", n
