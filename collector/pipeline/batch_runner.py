"""Ejecuta una tanda de búsquedas respetando ritmo y disyuntor."""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional

from collector.config.modelos import Config, Ubicacion
from collector.db import combinaciones_repo, consultas_repo, eventos_repo
from collector.db.connection import transaccion
from collector.linkedin import lectura
from collector.linkedin.errores import LimiteError, LinkedinError
from collector.filters.titulo import FiltroTitulos
from collector.pipeline import breaker, control
from collector.pipeline.ingest import ingerir
from collector.pipeline.ritmo import Ritmo
from collector.util.reloj import a_iso, de_iso



@dataclass
class ResultadoTanda:
    consultas: int = 0
    nuevas: int = 0
    combinaciones: int = 0
    limite: bool = False
    detenida_por: Optional[str] = None


def jobage_para(combo: sqlite3.Row, cfg: Config, ahora: datetime) -> int:
    """Primera vez: todo el periodo máximo. Después: solo lo publicado desde la última pasada, con margen."""
    maximo = cfg.lotes.entero("jobage_dias_primer_barrido")
    if not combo["ultima_ejecucion"]:
        return maximo
    dias = math.ceil((ahora - de_iso(combo["ultima_ejecucion"])) / timedelta(days=1))
    return max(1, min(maximo, dias + cfg.lotes.entero("margen_jobage_dias")))


def _hay_otra_pagina(n_resultados: int, n_nuevos: int, n_perfil: int, cfg: Config) -> bool:
    """Otra página si esta vino llena, con ofertas nuevas y con títulos del perfil (la relevancia cae página a página)."""
    return (n_resultados >= lectura.POR_PAGINA and n_nuevos / n_resultados >= cfg.lotes.decimal("umbral_pagina_nuevas")
            and n_perfil / n_resultados >= cfg.lotes.decimal("umbral_pagina_perfil"))


def _una_pagina(con: sqlite3.Connection, cfg: Config, cli, ritmo: Ritmo, combo: sqlite3.Row, ubic: Ubicacion,
                pagina: int, jobage: int, ahora: datetime):
    """Una petición y su registro. Devuelve (n_resultados, n_nuevos, n_perfil): cuántos títulos pasan el prefiltro."""
    ritmo.esperar()
    resultados = cli.buscar(combo["termino"], combo["ubicacion_frase"], jobage, cfg.modalidad.filtro,
                            pagina)
    with transaccion(con):
        estado = "ok" if resultados else "vacia"
        cid = consultas_repo.registrar(con, combo["combinacion_id"], pagina, jobage, a_iso(ahora), estado, len(resultados))
        nuevos = ingerir(con, cfg, ubic, cid, resultados, ahora)
        consultas_repo.fijar_nuevos(con, cid, nuevos)
    filtro = FiltroTitulos(cfg.prefiltro)
    return len(resultados), nuevos, sum(1 for r in resultados if not filtro.motivo_descarte(r.get("title") or ""))


def _registrar_error(con: sqlite3.Connection, combo: sqlite3.Row, pagina: int, jobage: int, ahora: datetime,
                     e: LinkedinError, limite: bool) -> None:
    with transaccion(con):
        consultas_repo.registrar(con, combo["combinacion_id"], pagina, jobage, a_iso(ahora),
                                 "desafio" if limite else "fallida", None, e.codigo)


def _procesar(con, cfg: Config, cli, ritmo: Ritmo, combo: sqlite3.Row, ubic: Ubicacion, ahora: datetime, restante: int):
    """Todas las páginas de una combinación. Devuelve (peticiones, nuevas, completa)."""
    jobage = jobage_para(combo, cfg, ahora)
    usadas = nuevas = 0
    for pagina in range(1, cfg.lotes.entero("max_paginas") + 1):
        fallos = 0
        while True:
            if usadas >= restante:
                return usadas, nuevas, False
            try:
                n_res, n_nuevos, n_perfil = _una_pagina(con, cfg, cli, ritmo, combo, ubic, pagina, jobage, ahora)
                break
            except LimiteError as e:
                _registrar_error(con, combo, pagina, jobage, ahora, e, True)
                raise
            except LinkedinError as e:
                _registrar_error(con, combo, pagina, jobage, ahora, e, False)
                usadas, fallos = usadas + 1, fallos + 1
                if not _reintentable(cfg, e, pagina, fallos):
                    return usadas, nuevas, False
        usadas, nuevas = usadas + 1, nuevas + n_nuevos
        if not _hay_otra_pagina(n_res, n_nuevos, n_perfil, cfg):
            break
    return usadas, nuevas, True


def _reintentable(cfg: Config, e: LinkedinError, pagina: int, fallos: int) -> bool:
    """Una lista sin tarjetas en la primera página se pide otra vez hasta `fallos_por_combinacion_para_saltar`; después se salta."""
    return (e.codigo == breaker.LISTA_SIN_TARJETAS and pagina == 1
            and fallos < cfg.lotes.entero("fallos_por_combinacion_para_saltar"))


def _cerrar(con: sqlite3.Connection, cfg: Config, combo: sqlite3.Row, ahora: datetime, nuevas: int, completa: bool) -> None:
    with transaccion(con):
        if completa:
            proxima = a_iso(ahora + timedelta(days=combo["cadencia_dias"]))
            combinaciones_repo.cerrar(con, combo["combinacion_id"], a_iso(ahora), proxima, nuevas > 0)
        else:
            horas = cfg.lotes.entero("reintento_fallida_horas")
            combinaciones_repo.reprogramar(con, combo["combinacion_id"], a_iso(ahora + timedelta(hours=horas)))


def _pedidor(con: sqlite3.Connection, cfg: Config, cli, ritmo: Ritmo, reloj: Callable[[], datetime]) -> control.Pedir:
    """La página 1 de una combinación para las búsquedas de control: con todo el periodo, registrada como cualquier otra."""
    def pedir(combo: sqlite3.Row) -> int:
        ubic, jobage, ahora = cfg.ubicacion_por_frase(combo["ubicacion_frase"]), cfg.lotes.entero("jobage_dias_primer_barrido"), reloj()
        try:
            return _una_pagina(con, cfg, cli, ritmo, combo, ubic, 1, jobage, ahora)[0]
        except LimiteError as e:
            _registrar_error(con, combo, 1, jobage, ahora, e, True)
            raise
        except LinkedinError as e:
            _registrar_error(con, combo, 1, jobage, ahora, e, False)
            raise
    return pedir


def _con_control(con: sqlite3.Connection, cfg: Config, res: ResultadoTanda, paso, ahora: datetime) -> bool:
    """Ejecuta un paso de control y anota sus peticiones. True si la tanda debe parar."""
    try:
        motivo, n = paso()
    except LimiteError:
        res.limite = True
        res.detenida_por = breaker.parar_por_limite(con, cfg, ahora, "búsqueda de control")
        return True
    res.consultas += n
    if motivo:
        res.detenida_por = motivo
    return motivo is not None


def _arrancar(con: sqlite3.Connection, cfg: Config, res: ResultadoTanda, pedir: control.Pedir,
              reloj: Callable[[], datetime]) -> bool:
    """Con una parada por sospecha (y nada más que lo impida), primero la búsqueda de control. True si se puede buscar."""
    ahora = reloj()
    if (breaker.hay_parada_por_sospecha(con, ahora) and breaker.en_horario_permitido(cfg, ahora)
            and not eventos_repo.otra_pausa_activa(con, a_iso(ahora), breaker.MARCA_SOSPECHA)):
        if _con_control(con, cfg, res, lambda: control.comprobar_al_arrancar(con, cfg, pedir, ahora), ahora):
            return False
    ok, razon = breaker.puede_ejecutar(con, cfg, reloj())
    if not ok:
        res.detenida_por = razon
    return ok


def ejecutar_tanda(con: sqlite3.Connection, cfg: Config, cli, ritmo: Ritmo,
                   reloj: Callable[[], datetime], max_consultas: int, una_combinacion: bool = False) -> ResultadoTanda:
    """Búsquedas hasta `max_consultas` peticiones; con `una_combinacion`, para tras la primera combinación."""
    res = ResultadoTanda()
    pedir = _pedidor(con, cfg, cli, ritmo, reloj)
    if not _arrancar(con, cfg, res, pedir, reloj):
        return res
    while max_consultas - res.consultas > 0:   # las búsquedas de control también cuentan
        restante = max_consultas - res.consultas
        debidas = combinaciones_repo.debidas(con, a_iso(reloj()), 1)
        if not debidas:
            res.detenida_por = "no hay combinaciones pendientes"
            break
        combo = debidas[0]
        ubic = cfg.ubicacion_por_frase(combo["ubicacion_frase"])
        if ubic is None:
            with transaccion(con):   # la ubicación ya no está en inputs/: se retira de la agenda
                combinaciones_repo.retirar(con, combo["combinacion_id"])
            continue
        ahora = reloj()
        try:
            usadas, nuevas, completa = _procesar(con, cfg, cli, ritmo, combo, ubic, ahora, restante)
        except LimiteError:
            res.limite = True
            res.detenida_por = breaker.parar_por_limite(con, cfg, ahora, f"{combo['termino']} @ {combo['ubicacion_frase']}")
            break
        _cerrar(con, cfg, combo, ahora, nuevas, completa)
        res.consultas, res.nuevas = res.consultas + usadas, res.nuevas + nuevas
        res.combinaciones += 1 if completa else 0
        if _con_control(con, cfg, res, lambda: control.revisar(con, cfg, pedir, ahora), ahora) or una_combinacion:
            break
    return res
