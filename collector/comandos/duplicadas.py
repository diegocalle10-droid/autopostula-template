"""Limpieza de un solo uso: la misma vacante publicada en varias ubicaciones (misma empresa y misma descripción).
Se conserva la más antigua de cada grupo y se borran las demás, en la base local y en Neon. Sin `--borrar` solo lista.
Las que vuelvan a aparecer las reconoce la captura al leer su detalle y las deja descartadas como duplicadas."""
from __future__ import annotations

from pathlib import Path

from collector.comandos import online
from collector.config.cargar import cargar_config
from collector.db import ofertas_repo
from collector.db.connection import conectar, transaccion
from collector.db.migrar import migrar
from collector.util.bloqueo import BloqueoError, bloqueo

SALIDA_BLOQUEADO = 4


def _listar(grupos) -> int:
    for g in grupos:
        o = g[0]
        print(f"Se conserva {o['job_id']} · {o['empresa']} · {o['titulo']} ({o['ubicacion']}, {o['estado']})")
        for f in g[1:]:
            print(f"   se borra {f['job_id']} ({f['ubicacion']}, {f['estado']})")
    copias = sum(len(g) - 1 for g in grupos)
    print(f"{len(grupos)} vacantes repetidas, {copias} copias.")
    return copias


def limpiar_duplicadas(args) -> int:
    cfg = cargar_config(args.inputs)
    con = conectar(args.db)
    migrar(con)
    grupos = ofertas_repo.grupos_por_contenido(con)
    copias = _listar(grupos)
    if not copias:
        return 0
    if not args.borrar:
        print("No se ha borrado nada. Para borrar las copias: python cli.py limpiar-duplicadas --borrar")
        return 0
    try:
        with bloqueo(Path(args.db).parent / ".lock", cfg.lotes.decimal("bloqueo_caduca_horas")):
            with transaccion(con):
                for g in grupos:
                    ofertas_repo.borrar_copias(con, g[0]["job_id"], [f["job_id"] for f in g[1:]])
    except BloqueoError as e:
        print(f"No se ejecuta: {e}")
        return SALIDA_BLOQUEADO
    print(f"Borradas {copias} copias en la base local. Se sube el borrado a Neon.")
    return online.online_subir(args)
