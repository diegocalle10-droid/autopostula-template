#!/usr/bin/env python3
"""Punto de entrada único. Uso: python cli.py <comando> [opciones]. Ver `python cli.py --help`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from collector.comandos import datos, ejecucion, instalacion, online
from collector.config.modelos import ConfigError

RAIZ = Path(__file__).resolve().parent


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cli.py", description="Recolector de ofertas de LinkedIn por lotes.")
    p.add_argument("--raiz", default=str(RAIZ), help="carpeta del proyecto")
    p.add_argument("--inputs", default=str(RAIZ / "inputs"), help="carpeta con las tablas de parámetros")
    p.add_argument("--db", default=str(RAIZ / "data" / "ofertas.sqlite"), help="archivo SQLite")
    sub = p.add_subparsers(dest="comando", required=True)
    _comandos_instalacion(sub)
    sub.add_parser("init-db", help="crea o actualiza la base de datos").set_defaults(f=datos.init_db)
    sub.add_parser("plan", help="sincroniza la agenda de búsquedas con inputs/").set_defaults(f=datos.plan)
    rv = sub.add_parser("reevaluar", help="aplica las reglas actuales a las aptas y por revisar con descripción (sin LinkedIn)")
    rv.add_argument("--dry-run", action="store_true", help="solo muestra qué cambiaría")
    rv.set_defaults(f=datos.reevaluar)
    sub.add_parser("prune", help="poda por rendimiento").set_defaults(f=datos.podar)
    sub.add_parser("status", help="peticiones del día, disyuntor y conteos").set_defaults(f=datos.status)
    sub.add_parser("doctor", help="comprueba el entorno, los secretos y los CV base").set_defaults(f=instalacion.doctor)
    sub.add_parser("sesion", help="comprueba la sesión de LinkedIn y, si hace falta, pide iniciarla").set_defaults(f=ejecucion.sesion)
    rn = sub.add_parser("reanudar", help="levanta las pausas del disyuntor")
    rn.add_argument("--forzar", action="store_true", help="levanta también una parada total")
    rn.set_defaults(f=datos.reanudar)
    r = sub.add_parser("run", help="ejecuta una tanda de búsquedas")
    r.add_argument("--max-consultas", type=int, default=0, help="peticiones máximas (por defecto, un lote)")
    r.add_argument("--dry-run", action="store_true", help="solo muestra qué haría")
    r.set_defaults(f=ejecucion.run)
    d = sub.add_parser("detail", help="pide y evalúa el detalle de ofertas nuevas")
    d.add_argument("--max", type=int, default=0, help="ofertas máximas (por defecto, un lote)")
    d.add_argument("--dry-run", action="store_true", help="solo muestra qué haría")
    d.set_defaults(f=ejecucion.detail)
    c = sub.add_parser("run-continuo", help="alterna búsquedas y detalles en un solo flujo, sin acumular ofertas sin detalle")
    c.add_argument("--horas", type=float, default=0, help="duración en horas (por defecto, horas_por_defecto de lotes.md)")
    c.add_argument("--max-pendientes", type=int, default=None,
                   help="ofertas elegibles sin detalle que se toleran antes de buscar (por defecto, inputs/lotes.md)")
    c.add_argument("--dry-run", action="store_true", help="solo muestra qué haría")
    c.set_defaults(f=ejecucion.run_continuo)
    _comandos_online(sub)
    return p


def _comandos_instalacion(sub) -> None:
    sub.add_parser("instalar", help="pone en marcha una instalación nueva: base local, agenda, Neon y comprobación").set_defaults(f=instalacion.instalar)
    sub.add_parser("validar-cv", help="muestra qué se reconoce de cada CV base y si sirve").set_defaults(f=instalacion.validar_cv)
    pt = sub.add_parser("probar-titulos", help="puntúa títulos de ejemplo con las familias de inputs/prefiltro.md")
    pt.add_argument("titulos", nargs="+", help="títulos entre comillas")
    pt.set_defaults(f=instalacion.probar_titulos)
    sub.add_parser("telegram-chat-id", help="muestra el TELEGRAM_CHAT_ID tras escribirle a tu bot").set_defaults(f=instalacion.telegram_chat_id)


def _comandos_online(sub) -> None:
    sub.add_parser("online-init", help="crea o actualiza el esquema en Neon").set_defaults(f=online.online_init)
    sub.add_parser("online-subir", help="sube a Neon lo pendiente (3 reintentos)").set_defaults(f=online.online_subir)
    sub.add_parser("online-estado", help="cola de subida y recuentos local/Neon").set_defaults(f=online.online_estado)
    op = sub.add_parser("online-pdf", help="valida los CV redactados en Neon y genera sus PDF (lo ejecuta GitHub Actions)")
    op.add_argument("--salida", default="CV/pdf", help="carpeta de los PDF, relativa a la raíz")
    op.add_argument("--max", type=int, default=50)
    op.add_argument("--fuente", choices=("manual", "rutina"), default="manual",
                    help="quién la lanza; con «rutina» se envía además el resumen de la ejecución")
    op.set_defaults(f=online.online_pdf)


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.f(args)
    except ConfigError as e:
        print(f"Error de configuración: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
