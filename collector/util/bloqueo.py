"""Un solo proceso a la vez: archivo de bloqueo con caducidad, para que dos ejecuciones no se pisen."""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class BloqueoError(Exception):
    """Ya hay otra ejecución en curso."""


def _tomar(ruta: Path, caduca_horas: float) -> None:
    for _ in range(2):
        try:
            fd = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                antiguedad = time.time() - ruta.stat().st_mtime
            except FileNotFoundError:
                continue   # lo soltaron justo ahora: se reintenta
            if antiguedad < caduca_horas * 3600:
                raise BloqueoError(f"ya hay otra ejecución en curso ({ruta}). Si no es así, borra ese archivo.") from None
            ruta.unlink(missing_ok=True)   # abandonado por una ejecución que murió
            continue
        with os.fdopen(fd, "w") as f:
            f.write(str(os.getpid()))
        return
    raise BloqueoError(f"no se pudo tomar el bloqueo ({ruta})")


@contextmanager
def bloqueo(ruta, caduca_horas: float) -> Iterator[None]:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    _tomar(ruta, caduca_horas)
    try:
        yield
    finally:
        ruta.unlink(missing_ok=True)
