"""Comandos de la base online (Neon): online-init, online-subir, online-pdf y online-estado."""
from __future__ import annotations

from pathlib import Path

from collector.config.cargar import cargar_config
from collector.db.connection import conectar
from collector.db.migrar import migrar
from collector.online import avisos, conexion, esquema, mensajes, notificador, pdfs, rutina, subir
from collector.util import reloj

TABLAS_EMPAREJADAS = subir.ORDEN + ["emparejamientos"]


def _sin_url() -> int:
    print(f"Falta {conexion.VARIABLE} (en el entorno o en .env). No se toca Neon.")
    return 1


def online_init(args) -> int:
    abrir = conexion.abridor(args.raiz)
    if not abrir:
        return _sin_url()
    pg = abrir()
    try:
        aplicadas = esquema.migrar(pg)
        print(f"Esquema de Neon en versión {esquema.version_actual(pg)}" + (f" (aplicadas: {aplicadas})" if aplicadas else " (al día)"))
    finally:
        pg.close()
    return 0


def online_subir(args) -> int:
    abrir = conexion.abridor(args.raiz)
    if not abrir:
        return _sin_url()
    con = conectar(args.db)
    migrar(con)
    ok = subir.con_reintentos(con, abrir)
    print("Subida completa." if ok else "Subida incompleta; queda en la cola.")
    return 0 if ok else 5


def online_pdf(args) -> int:
    """Valida las redactadas de Neon, genera y envía sus PDF; después, avisos de sin CV, rechazos y (si la disparó
    la rutina) su resumen. Los textos salen de la bandeja `avisos`: lo que no se envíe ahora sale en la próxima pasada."""
    abrir = conexion.abridor(args.raiz)
    if not abrir:
        return _sin_url()
    cfg = cargar_config(args.inputs)
    notif = notificador.cargar(args.raiz)
    if not notif:
        print("Aviso: faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID; se valida y se encola, pero no se envía.")
    instante = reloj.ahora()
    ahora = reloj.a_iso(instante)
    pg = abrir()
    try:
        r = pdfs.procesar(pg, cfg, Path(args.raiz), Path(args.raiz) / args.salida, ahora, args.max,
                          enviar=notif.documento if notif else None)
        sin_cv = rutina.encolar_sin_cv(pg, ahora)
        cierre = rutina.encolar_resumen(pg, mensajes.fecha(instante)) if args.fuente == "rutina" else "-"
        textos = avisos.enviar_pendientes(pg, notif.texto, ahora) if notif else 0
    finally:
        pg.close()
    print(f"Validadas {len(r['validadas'])}, rechazadas {len(r['rechazadas'])}, PDF enviados {len(r['avisadas'])}; "
          f"sin CV avisadas {sin_cv}; cierre de rutina: {cierre}; textos enviados {textos}.")
    return 0


def online_estado(args) -> int:
    con = conectar(args.db)
    migrar(con)
    cola = subir.total_pendientes(con)
    print("Cola de subida: " + (", ".join(f"{t} {n}" for t, n in cola.items()) if cola else "vacía"))
    abrir = conexion.abridor(args.raiz)
    if not abrir:
        return _sin_url()
    pg = abrir()
    try:
        cur = pg.cursor()
        print(f"{'tabla':22}{'local':>8}{'Neon':>8}")
        for t in TABLAS_EMPAREJADAS:
            local = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if t in subir.ORDEN else "-"
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            print(f"{t:22}{local!s:>8}{cur.fetchone()[0]:>8}")
        cur.execute("SELECT estado, COUNT(*) FROM ofertas GROUP BY estado ORDER BY estado")
        print("ofertas en Neon por estado: " + ", ".join(f"{e} {n}" for e, n in cur.fetchall()))
    finally:
        pg.close()
    return 0
