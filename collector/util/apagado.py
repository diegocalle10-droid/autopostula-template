"""Apagado del PC al terminar la captura (solo Windows): programa `shutdown /s` con un margen para poder cancelarlo."""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta
from typing import Callable, Optional


def programar(minutos: int, ahora: datetime, ejecutar: Callable = subprocess.run, sistema: str = os.name) -> Optional[datetime]:
    """Instante del apagado, o None si está desactivado (0 minutos), no es Windows o el sistema lo rechaza.
    `shutdown /a` lo cancela."""
    if minutos <= 0 or sistema != "nt":
        return None
    try:
        r = ejecutar(["shutdown", "/s", "/t", str(minutos * 60)], capture_output=True, check=False)
    except OSError:
        return None
    return ahora + timedelta(minutes=minutos) if getattr(r, "returncode", 1) == 0 else None
