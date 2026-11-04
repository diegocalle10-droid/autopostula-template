"""Comandos que hacen peticiones a LinkedIn: run, detail y run-continuo. Todos admiten --dry-run y toman el bloqueo."""
from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path

from collector.comandos import captura
from collector.config.cargar import cargar_config
from collector.db import combinaciones_repo, ofertas_repo
from collector.db.connection import conectar, transaccion
from collector.db.migrar import migrar
from collector.linkedin.errores import LinkedinError
from collector.linkedin.sesion_runner import LinkedinSesion
from collector.online import mensajes, notificador
from collector.pipeline import ingest, prune, seleccion
from collector.pipeline.batch_runner import ejecutar_tanda
from collector.pipeline.detail_runner import procesar_detalles
from collector.pipeline.flujo import Flujo, resumen
from collector.pipeline.ritmo import Ritmo
from collector.util import reloj
from collector.util.bloqueo import BloqueoError, bloqueo

SALIDA_LIMITE = 2
SALIDA_BLOQUEADO = 4
SALIDA_SESION = 5


def _ritmo(cfg, prefijo: str, lote: int) -> Ritmo:
    l = cfg.lotes
    sufijo = "_detail" if prefijo == "detail" else ""
    return Ritmo(lote, (l.entero(f"pausa_entre_{prefijo}_min"), l.entero(f"pausa_entre_{prefijo}_max")),
                 (l.entero(f"pausa_entre_lotes{sufijo}_min"), l.entero(f"pausa_entre_lotes{sufijo}_max")))


def _con_bloqueo(args, cfg, accion) -> int:
    """Ejecuta `accion` si no hay otra ejecución en curso."""
    try:
        with bloqueo(Path(args.db).parent / ".lock", cfg.lotes.decimal("bloqueo_caduca_horas")):
            return accion()
    except BloqueoError as e:
        print(f"No se ejecuta: {e}")
        return SALIDA_BLOQUEADO
    except LinkedinError as e:   # sin sesión válida no hay captura
        print(f"No se ejecuta: {e.mensaje}")
        return SALIDA_SESION


def _avisador(args):
    return notificador.avisador(args.raiz, mensajes.aviso_linkedin)


def sesion(args) -> int:
    """Abre LinkedIn con el perfil guardado y aplica el protocolo de sesión (inicio de sesión si hace falta)."""
    cfg = cargar_config(args.inputs)
    resultado = _con_bloqueo(args, cfg, lambda: _abrir_y_cerrar(args, cfg))
    if resultado == 0:
        print("Sesión de LinkedIn válida.")
    return resultado


def _abrir_y_cerrar(args, cfg) -> int:
    with LinkedinSesion(args.raiz, cfg, _avisador(args)):
        return 0


def run(args) -> int:
    cfg = cargar_config(args.inputs)
    con = conectar(args.db)
    migrar(con)
    maximo = args.max_consultas or cfg.lotes.entero("consultas_por_lote")
    if args.dry_run:
        for c in combinaciones_repo.debidas(con, reloj.a_iso(reloj.ahora()), maximo):
            print(f"[simulacro] P{c['prioridad']}  {c['termino']!r} @ {c['ubicacion_frase']}")
        print("[simulacro] no se ha hecho ninguna petición.")
        return 0
    return _con_bloqueo(args, cfg, lambda: _tanda(args, cfg, con, maximo))


def _tanda(args, cfg, con, maximo: int) -> int:
    with LinkedinSesion(args.raiz, cfg, _avisador(args)) as cli:
        r = ejecutar_tanda(con, cfg, cli, _ritmo(cfg, "consultas", cfg.lotes.entero("consultas_por_lote")),
                           reloj.ahora, maximo)
    with transaccion(con):   # la poda se aplica sola tras cada tanda
        prune.podar(con, cfg)
    print(f"Tanda: {r.consultas} peticiones, {r.nuevas} ofertas nuevas, {r.combinaciones} combinaciones completas.")
    if r.detenida_por:
        print(f"Detenida: {r.detenida_por}")
    return SALIDA_LIMITE if r.limite else 0


def detail(args) -> int:
    cfg = cargar_config(args.inputs)
    con = conectar(args.db)
    migrar(con)
    maximo = args.max or cfg.lotes.entero("detail_por_lote")
    if args.dry_run:
        sel = seleccion.seleccionar(ofertas_repo.pendientes_de_detalle(con), cfg, maximo)
        for e in sel.elegibles:
            print(f"[simulacro] país P{e.prioridad_pais} · título {e.puntos} pts  {e.oferta['job_id']}  {e.oferta['titulo']}")
        print(f"[simulacro] elegibles en total: {sel.total_elegibles}; en espera de confirmar país: {sel.en_espera.get('pais_sin_confirmar', 0)}; "
              f"se descartarían por título: {ingest.por_descartar_por_titulo(con, cfg)}")
        print("[simulacro] no se ha hecho ninguna petición.")
        return 0
    return _con_bloqueo(args, cfg, lambda: _detalles(args, cfg, con, maximo))


def _filtrar_titulos(con, cfg) -> None:
    """Antes de pedir detalles: las pendientes cuyo título está fuera del perfil quedan descartadas."""
    with transaccion(con):
        n = ingest.descartar_por_titulo(con, cfg)
    if n:
        print(f"Descartadas por título fuera del perfil: {n}", flush=True)


def _detalles(args, cfg, con, maximo: int) -> int:
    _filtrar_titulos(con, cfg)
    captura.subir_si_hay(args, con, "Al arrancar")
    with LinkedinSesion(args.raiz, cfg, _avisador(args)) as cli:
        r = procesar_detalles(con, cfg, cli, _ritmo(cfg, "detail", cfg.lotes.entero("detail_por_lote")), reloj.ahora, maximo)
    print(f"Detalle: {r.procesadas} evaluadas (aptas {r.aptas}, revisar {r.revisar}, descartadas {r.descartadas}).")
    if r.detenida_por:
        print(f"Detenido: {r.detenida_por}")
    captura.cerrar_detalles(args, con, r)   # sube a Neon y avisa por Telegram
    return SALIDA_LIMITE if r.limite else 0


def run_continuo(args) -> int:
    cfg = cargar_config(args.inputs)
    con = conectar(args.db)
    migrar(con)
    if args.dry_run:
        n = cfg.lotes.entero("detalles_pendientes_max") if args.max_pendientes is None else args.max_pendientes
        elegibles = seleccion.seleccionar(ofertas_repo.pendientes_de_detalle(con), cfg).total_elegibles
        print(f"[simulacro] elegibles sin detalle: {elegibles}; se toleran {n} antes de volver a buscar; "
              f"se descartarían por título: {ingest.por_descartar_por_titulo(con, cfg)}")
        print(f"[simulacro] primera petición: {'detalle' if elegibles > n else 'búsqueda'}; no se ha hecho ninguna.")
        return 0
    args.horas = captura.preguntar_horas(args.horas, cfg.lotes.decimal("horas_por_defecto"))
    return _con_bloqueo(args, cfg, lambda: _flujo(args, cfg, con))


def _flujo(args, cfg, con) -> int:
    _filtrar_titulos(con, cfg)
    fin = reloj.ahora() + timedelta(hours=args.horas)
    with LinkedinSesion(args.raiz, cfg, _avisador(args)) as cli:
        flujo = Flujo(con, cfg, cli, reloj.ahora, time.sleep, fin=fin, max_pendientes=args.max_pendientes,
                      log=lambda m: print(m, flush=True))
        r = captura.ejecutar(args, con, flujo, cfg.lotes.entero("apagar_tras_captura_min"))   # sube al empezar y al terminar (también si se corta) y avisa
    print(resumen(r), flush=True)
    return SALIDA_LIMITE if r.limite else 0
