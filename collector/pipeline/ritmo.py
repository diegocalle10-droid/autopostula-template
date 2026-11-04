"""Ritmo de las peticiones: pausas aleatorias dentro de un lote y entre lotes."""
from __future__ import annotations

import random
import time
from typing import Callable


class Ritmo:
    """Llamar a `esperar()` antes de cada petición. La primera no espera; cada `por_lote` hay pausa larga."""

    def __init__(self, por_lote: int, corta_s: tuple, larga_min: tuple,
                 dormir: Callable[[float], None] = time.sleep,
                 azar: Callable[[float, float], float] = random.uniform):
        self._por_lote = por_lote
        self._corta = corta_s
        self._larga = larga_min
        self._dormir = dormir
        self._azar = azar
        self.peticiones = 0

    def esperar(self) -> float:
        """Devuelve los segundos que ha esperado (para registrarlo y para probar)."""
        espera = 0.0
        if self.peticiones > 0:
            if self.peticiones % self._por_lote == 0:
                espera = self._azar(self._larga[0] * 60, self._larga[1] * 60)
            else:
                espera = self._azar(*self._corta)
            self._dormir(espera)
        self.peticiones += 1
        return espera

