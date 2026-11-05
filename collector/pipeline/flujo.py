"""Flujo continuo: una sola cadena de peticiones que alterna búsquedas y detalles para que no se acumulen ofertas
sin detalle. Antes de cada petición se decide: si hay más ofertas elegibles sin detalle que `detalles_pendientes_max`,
se pide un detalle; si no, se hace una búsqueda (una combinación entera, de 1 a `max_paginas` peticiones)."""
from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional

from collector.config.modelos import Config
from collector.db import ofertas_repo
from collector.db.connection import transaccion
from collector.pipeline import breaker, prune, seleccion
from collector.pipeline.batch_runner import ejecutar_tanda
from collector.pipeline.detail_runner import procesar_detalles
from collector.pipeline.ritmo import Ritmo

BUSQUEDA, DETALLE = "B", "D"
AGENDA_VACIA = "no hay combinaciones pendientes"


@dataclass
class ResultadoFlujo:
    busquedas: int = 0        # peticiones de búsqueda
    detalles: int = 0         # detalles evaluados
    nuevas: int = 0
    aptas: int = 0
    revisar: int = 0
    descartadas: int = 0
    acumulado_max: int = 0    # mayor número de ofertas elegibles sin detalle visto a la vez
    secuencia: str = ""       # una letra por petición: B búsqueda, D detalle
    limite: bool = False
    motivo: Optional[str] = None


class Flujo:
    def __init__(self, con: sqlite3.Connection, cfg: Config, cli, reloj: Callable[[], datetime],
                 dormir: Callable[[float], None], fin: Optional[datetime] = None,
                 max_pendientes: Optional[int] = None, azar: Callable[[float, float], float] = random.uniform,
                 log: Callable[[str], None] = print):
        self.con, self.cfg, self.cli, self.reloj, self.dormir, self.fin = con, cfg, cli, reloj, dormir, fin
        self.azar, self.log = azar, log
        self.n = cfg.lotes.entero("detalles_pendientes_max") if max_pendientes is None else max_pendientes
        self.res = ResultadoFlujo()
        self._agenda_vacia = False
        self._fallos_detalle = 0

    def _elegibles(self) -> int:
        return seleccion.seleccionar(ofertas_repo.pendientes_de_detalle(self.con), self.cfg).total_elegibles

    def _siguiente(self, elegibles: int) -> str:
        if breaker.hay_parada_por_sospecha(self.con, self.reloj()):
            return BUSQUEDA   # la búsqueda de control con la que arranca la tanda decide si se sigue
        if elegibles > self.n or (self._agenda_vacia and elegibles > 0):
            return DETALLE
        return BUSQUEDA

    def _rango(self, accion: str) -> tuple:
        base = "pausa_entre_consultas" if accion == BUSQUEDA else "pausa_entre_detail"
        return self.cfg.lotes.entero(f"{base}_min"), self.cfg.lotes.entero(f"{base}_max")

    def _pausa(self, accion: str) -> bool:
        """Espera antes de la petición. False si la espera pasaría de la hora de fin."""
        segundos = self.azar(*self._rango(accion))
        if self.fin is not None and self.reloj() + timedelta(seconds=segundos) >= self.fin:
            self.res.motivo = "tiempo cumplido"
            return False
        self.dormir(segundos)
        return True

    def _buscar(self) -> bool:
        ritmo = Ritmo(10 ** 9, self._rango(BUSQUEDA), (0, 0), dormir=self.dormir, azar=self.azar)  # páginas siguientes
        r = ejecutar_tanda(self.con, self.cfg, self.cli, ritmo, self.reloj,
                           self.cfg.lotes.entero("max_paginas"), una_combinacion=True)
        with transaccion(self.con):
            prune.podar(self.con, self.cfg)
        self.res.busquedas, self.res.nuevas = self.res.busquedas + r.consultas, self.res.nuevas + r.nuevas
        self.res.secuencia += BUSQUEDA * r.consultas
        if r.consultas:
            self.log(f"[{self.reloj():%H:%M}] búsqueda: {r.consultas} peticiones, {r.nuevas} ofertas nuevas")
        if r.detenida_por == AGENDA_VACIA:
            self._agenda_vacia = True
            return True
        self.res.limite = r.limite
        self.res.motivo = r.detenida_por
        return r.detenida_por is None

    def _detallar(self) -> bool:
        r = procesar_detalles(self.con, self.cfg, self.cli, Ritmo(10 ** 9, (0, 0), (0, 0), dormir=self.dormir),
                              self.reloj, 1)
        self.res.secuencia += DETALLE
        self.res.detalles += r.procesadas
        self.res.aptas, self.res.revisar = self.res.aptas + r.aptas, self.res.revisar + r.revisar
        self.res.descartadas += r.descartadas
        estado = "apta" if r.aptas else "revisar" if r.revisar else "descartada" if r.descartadas else "fallo"
        self.log(f"[{self.reloj():%H:%M}] detalle: {estado}")
        if r.detenida_por:
            self.res.limite, self.res.motivo = r.limite, r.detenida_por
            return False
        return self._contar_fallo(r.procesadas == 0 or r.ilegibles > 0)

    def _contar_fallo(self, fallo: bool) -> bool:
        """Cada detalle se pide por separado, así que los fallos seguidos se cuentan aquí; descartar una oferta ilegible
        también cuenta, para que un fallo general no vaya descartando la cola. False si hay que parar."""
        self._fallos_detalle = self._fallos_detalle + 1 if fallo else 0
        maximo = self.cfg.lotes.entero("fallos_seguidos_para_parada")
        if self._fallos_detalle < maximo:
            return True
        with transaccion(self.con):
            breaker.parar_por_sospecha(self.con, self.reloj(), f"{maximo} fallos seguidos en el detalle")
        self.res.motivo = "fallos seguidos en el detalle"
        return False

    def ejecutar(self) -> ResultadoFlujo:
        primera = True
        while True:
            elegibles = self._elegibles()
            self.res.acumulado_max = max(self.res.acumulado_max, elegibles)
            accion = self._siguiente(elegibles)
            if accion == BUSQUEDA and self._agenda_vacia:
                self.res.motivo = "agenda agotada y sin detalles pendientes"
                return self.res
            if not primera and not self._pausa(accion):
                return self.res
            primera = False
            if not (self._buscar() if accion == BUSQUEDA else self._detallar()):
                return self.res


def resumen(r: ResultadoFlujo) -> str:
    por_busqueda = f"{r.detalles / r.busquedas:.1f}" if r.busquedas else "-"
    return (f"\nFlujo terminado: {r.motivo}\n"
            f"  peticiones: {len(r.secuencia)} (búsquedas {r.busquedas}, detalles {r.secuencia.count(DETALLE)}); "
            f"detalles evaluados por búsqueda: {por_busqueda}\n"
            f"  ofertas nuevas {r.nuevas}; aptas {r.aptas}, revisar {r.revisar}, descartadas {r.descartadas}\n"
            f"  acumulado máximo de ofertas elegibles sin detalle: {r.acumulado_max}\n"
            f"  secuencia: {r.secuencia[:80]}{'…' if len(r.secuencia) > 80 else ''}")
