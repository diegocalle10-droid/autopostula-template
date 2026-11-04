"""Fechas y horas. Todo se guarda en UTC con formato ISO-8601 (por ejemplo 2026-10-27T14:03:00Z)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

FORMATO = "%Y-%m-%dT%H:%M:%SZ"


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def a_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(FORMATO)


def de_iso(texto: str) -> datetime:
    return datetime.strptime(texto, FORMATO).replace(tzinfo=timezone.utc)


def inicio_dia_local(dt: datetime) -> datetime:
    """Medianoche local del día de `dt`, expresada en UTC. El recuento diario se cuenta por día local."""
    local = dt.astimezone()
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def inicio_dia_siguiente_local(dt: datetime) -> datetime:
    """Medianoche local del día siguiente, expresada en UTC."""
    manana = dt.astimezone().date() + timedelta(days=1)
    return datetime(manana.year, manana.month, manana.day).astimezone().astimezone(timezone.utc)

