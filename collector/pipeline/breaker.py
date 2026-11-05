"""Disyuntor: decide si se pueden lanzar peticiones y registra los incidentes."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Tuple

from collector.config.modelos import Config
from collector.db import eventos_repo
from collector.db.connection import transaccion
from collector.util.reloj import a_iso, inicio_dia_local, inicio_dia_siguiente_local


LISTA_SIN_TARJETAS = "LISTA_SIN_TARJETAS"   # fallo de la página de esa combinación: se pide otra vez y se salta
MARCA_SOSPECHA = "[parada_sospecha]"
SIN_PLAZO = "9999-12-31T00:00:00Z"            # la parada por sospecha no caduca sola


def puede_ejecutar(con: sqlite3.Connection, cfg: Config, ahora: datetime) -> Tuple[bool, str]:
    pausa = eventos_repo.pausa_activa(con, a_iso(ahora))
    if pausa and pausa["pausa_hasta"] == SIN_PLAZO:
        return False, f"parada hasta reanudar: {pausa['contexto']}"
    if pausa:
        return False, f"pausa activa por «{pausa['tipo']}» hasta {pausa['pausa_hasta']}"
    return True, ""


def en_horario_permitido(cfg: Config, ahora: datetime) -> bool:
    """Sin franja horaria: la captura dura las horas que se le piden (`horas_por_defecto`)."""
    return True


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


def parar_por_sospecha(con: sqlite3.Connection, ahora: datetime, contexto: str) -> None:
    """Parada sin plazo: algo falla en todo el sistema (no en una combinación). Solo la levanta `reanudar` o la búsqueda
    de control con la que arranca la siguiente captura. El contexto no debe empezar por «detail »: ese prefijo cuenta
    como petición de detalle."""
    eventos_repo.registrar(con, "fallo", a_iso(ahora), f"{contexto} {MARCA_SOSPECHA}", SIN_PLAZO)


def hay_parada_por_sospecha(con: sqlite3.Connection, ahora: datetime) -> Optional[sqlite3.Row]:
    return eventos_repo.pausa_activa_con(con, a_iso(ahora), MARCA_SOSPECHA)


def hay_parada_total(con: sqlite3.Connection, ahora: datetime) -> Optional[sqlite3.Row]:
    """El evento de parada total vigente, si lo hay."""
    return eventos_repo.pausa_activa_con(con, a_iso(ahora), "[parada_total]")
