"""Disyuntor: decide si se pueden lanzar peticiones y registra los incidentes."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Tuple

from collector.config.modelos import Config
from collector.db import consultas_repo, eventos_repo
from collector.db.connection import transaccion
from collector.util.reloj import a_iso, inicio_dia_local, inicio_dia_siguiente_local


LISTA_SIN_TARJETAS = "LISTA_SIN_TARJETAS"   # fallo de la página de esa combinación: se salta, no pausa la ejecución


def puede_ejecutar(con: sqlite3.Connection, cfg: Config, ahora: datetime) -> Tuple[bool, str]:
    pausa = eventos_repo.pausa_activa(con, a_iso(ahora))
    if pausa:
        return False, f"pausa activa por «{pausa['tipo']}» hasta {pausa['pausa_hasta']}"
    return True, ""


def registrar_limite(con: sqlite3.Connection, cfg: Config, ahora: datetime, contexto: str) -> str:
    """Un 429 o desafío anti-bot: aplica el primer escalón de la tabla «Escalada del 429» que se cumple."""
    for e in cfg.escalada_429:
        desde = inicio_dia_local(ahora) if e.ventana_dias == 0 else ahora - timedelta(days=e.ventana_dias)
        if eventos_repo.contar(con, "429", a_iso(desde)) + 1 >= e.ocurrencias:
            hasta = inicio_dia_siguiente_local(ahora) if e.accion == "hasta_manana" else ahora + timedelta(hours=e.horas)
            eventos_repo.registrar(con, "429", a_iso(ahora), f"{contexto} [{e.accion}]", a_iso(hasta))
            return e.accion
    raise ValueError("escalada del 429 sin escalón para la primera ocurrencia")   # la carga de inputs lo impide


def parar_por_limite(con: sqlite3.Connection, cfg: Config, ahora: datetime, contexto: str) -> str:
    """Registra el 429 en su propia transacción y devuelve el motivo de parada para mostrar."""
    with transaccion(con):
        accion = registrar_limite(con, cfg, ahora, contexto)
    return f"429/desafío anti-bot ({accion})"


def _pausar(con: sqlite3.Connection, cfg: Config, ahora: datetime, tipo: str, contexto: str, clave_horas: str) -> None:
    hasta = ahora + timedelta(hours=cfg.lotes.entero(clave_horas))
    eventos_repo.registrar(con, tipo, a_iso(ahora), contexto, a_iso(hasta))


def revisar_vacios(con: sqlite3.Connection, cfg: Config, ahora: datetime) -> bool:
    """N consultas seguidas vacías, habiendo devuelto datos antes: posible cambio de HTML o bloqueo blando."""
    n = cfg.lotes.entero("vacios_seguidos_para_alerta")
    ultimas = consultas_repo.ultimas(con, n)
    if len(ultimas) < n or any(u["resultado"] != "vacia" for u in ultimas):
        return False
    if not consultas_repo.hubo_resultados_alguna_vez(con):
        return False
    _pausar(con, cfg, ahora, "vacios_repetidos", f"{n} consultas vacías seguidas", "pausa_tras_vacios_horas")
    return True


def revisar_fallos(con: sqlite3.Connection, cfg: Config, ahora: datetime) -> bool:
    """N consultas seguidas fallidas (sin ser 429 ni lista sin tarjetas, que solo salta la combinación): pausa."""
    n = cfg.lotes.entero("fallos_seguidos_para_parada")
    ultimas = consultas_repo.ultimas(con, n)
    if len(ultimas) < n or any(u["resultado"] != "fallida" or u["codigo_error"] == LISTA_SIN_TARJETAS for u in ultimas):
        return False
    parar_por_fallos(con, cfg, ahora, f"{n} fallos seguidos")
    return True


def parar_por_fallos(con: sqlite3.Connection, cfg: Config, ahora: datetime, contexto: str) -> None:
    """Pausa por fallos seguidos (sin ser 429). El contexto no debe empezar por «detail »: ese prefijo cuenta como petición de detalle."""
    _pausar(con, cfg, ahora, "fallo", contexto, "pausa_tras_fallos_horas")


def hay_parada_total(con: sqlite3.Connection, ahora: datetime) -> Optional[sqlite3.Row]:
    """El evento de parada total vigente, si lo hay."""
    return eventos_repo.pausa_activa_con(con, a_iso(ahora), "[parada_total]")
