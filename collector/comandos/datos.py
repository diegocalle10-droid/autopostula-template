"""Comandos que no hacen peticiones a LinkedIn: init-db, plan, reevaluar, prune, status, doctor (la parte del entorno) y reanudar."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from collector.config.cargar import cargar_config
from collector.config.modelos import ConfigError
from collector.db import combinaciones_repo, eventos_repo, ofertas_repo
from collector.db.connection import conectar, transaccion
from collector.db.migrar import migrar, version_actual
from collector.linkedin import sesion
from collector.linkedin.sesion_runner import PERFIL
from collector.pipeline import breaker, cuota, ingest, plan_builder, prune, seleccion
from collector.pipeline.reevaluar import reevaluar as reevaluar_ofertas
from collector.util import reloj


def init_db(args) -> int:
    con = conectar(args.db)
    aplicadas = migrar(con)
    print(f"Base de datos: {args.db}")
    print(f"Versión del esquema: {version_actual(con)}" + (f" (aplicadas: {aplicadas})" if aplicadas else " (al día)"))
    return 0


def plan(args) -> int:
    cfg = cargar_config(args.inputs)
    con = conectar(args.db)
    migrar(con)
    with transaccion(con):
        r = plan_builder.sincronizar(con, cfg, reloj.ahora())
        fuera = ingest.descartar_por_titulo(con, cfg)   # si cambió prefiltro.md, se aplica a las pendientes
    print(f"Agenda sincronizada: {r['total']} combinaciones previstas, {r['nuevas']} nuevas, {r['retiradas']} retiradas.")
    if fuera:
        print(f"Descartadas por título fuera del perfil: {fuera}")
    return 0


def reevaluar(args) -> int:
    """Aplica las reglas actuales a las aptas y por revisar con descripción, sin pedir nada a LinkedIn."""
    cfg = cargar_config(args.inputs)
    con = conectar(args.db)
    migrar(con)
    if args.dry_run:
        cambios = reevaluar_ofertas(con, cfg, aplicar=False)
    else:
        with transaccion(con):
            cambios = reevaluar_ofertas(con, cfg, aplicar=True)
    for (antes, despues), n in sorted(cambios.items(), key=lambda x: -x[1]):
        print(f"  {n:3}  {antes}  ->  {despues}")
    total = sum(cambios.values())
    print(f"{'[simulacro] cambiarían' if args.dry_run else 'Cambiadas'}: {total}" + ("" if total else " (nada que cambiar)"))
    return 0


def podar(args) -> int:
    cfg = cargar_config(args.inputs)
    con = conectar(args.db)
    with transaccion(con):
        r = prune.podar(con, cfg)
    print(f"Poda: {r['ubicaciones_espaciadas']} ubicaciones espaciadas, "
          f"{r['cadencias_duplicadas']} cadencias duplicadas, {r['recuperadas']} recuperadas.")
    return 0


def reanudar(args) -> int:
    con = conectar(args.db)
    parada = breaker.hay_parada_total(con, reloj.ahora())
    if parada and not args.forzar:
        print(f"Hay una parada total vigente ({parada['contexto']}). Revisa `status`; si aun así quieres seguir, usa --forzar.")
        return 1
    with transaccion(con):
        n = eventos_repo.cancelar_pausas(con, reloj.a_iso(reloj.ahora()))
    print(f"Pausas levantadas: {n}. Úsalo solo si sabes por qué se pausó (ver `status`).")
    return 0


def status(args) -> int:
    cfg = cargar_config(args.inputs)
    con = conectar(args.db)
    migrar(con)
    ahora = reloj.ahora()
    print(f"Esquema v{version_actual(con)}")
    c = combinaciones_repo.contar(con)
    print(f"Agenda: {c['activas']} combinaciones activas de {c['total']}; "
          f"{combinaciones_repo.contar_debidas(con, reloj.a_iso(ahora))} pendientes de ejecutar")
    u = cuota.usadas_hoy(con, ahora)
    print(f"Peticiones hoy: {sum(u.values())} (búsquedas {u['busquedas']}, detalles {u['detalles']})")
    sel = seleccion.seleccionar(ofertas_repo.pendientes_de_detalle(con), cfg)
    print(f"Detalle pendiente: {sel.total_elegibles} elegibles, en espera de confirmar país {sel.en_espera.get('pais_sin_confirmar', 0)}, "
          f"por descartar por título {ingest.por_descartar_por_titulo(con, cfg)}")
    print(f"Ofertas por estado: {ofertas_repo.contar_por_estado(con) or 'ninguna'}")
    pausa = eventos_repo.pausa_activa(con, reloj.a_iso(ahora))
    print("Disyuntor: " + (f"PAUSADO por «{pausa['tipo']}» hasta {pausa['pausa_hasta']} ({pausa['contexto']})" if pausa else "libre"))
    return 0


def _comprobar_navegador(raiz) -> int:
    """Playwright y Chrome instalados y sesión de LinkedIn validada hoy; devuelve cuántas comprobaciones fallan."""
    fallos = 0
    if importlib.util.find_spec("playwright"):
        print("OK   playwright instalado")
    else:
        print("FALLA playwright: pip install -r requirements-captura.txt")
        fallos += 1
    chrome = any(Path(r).exists() for r in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                                            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"))
    print(("OK  " if chrome else "FALLA") + " Chrome instalado")
    fallos += 0 if chrome else 1
    perfil = Path(raiz).joinpath(*PERFIL)
    hoy = reloj.ahora().astimezone().date().isoformat()
    print("OK   sesión de LinkedIn validada hoy" if sesion.validada_hoy(perfil, hoy) else
          "AVISO la sesión de LinkedIn no se ha validado hoy: se comprueba sola al empezar la captura (o con «python cli.py sesion»)")
    return fallos


def doctor(args) -> int:
    fallos = 0
    try:
        cfg = cargar_config(args.inputs)
        print(f"OK   inputs/: {len(cfg.ubicaciones)} ubicaciones, {len(cfg.terminos)} términos")
    except ConfigError as e:
        print(f"FALLA inputs/: {e}")
        fallos += 1
    fallos += _comprobar_navegador(args.raiz)
    con = conectar(args.db)
    print(f"OK   base de datos {args.db} (esquema v{version_actual(con)})")
    return 1 if fallos else 0
