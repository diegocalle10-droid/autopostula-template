"""Guarda en la base de datos los resultados de una búsqueda y aplica el filtro de título (inputs/prefiltro.md):
un título fuera del perfil entra ya descartado, con su motivo, sin gastar una petición de detalle."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from collector.config.modelos import Config, Ubicacion
from collector.db import consultas_repo, ofertas_repo
from collector.estados import DESCARTADA, PENDIENTE
from collector.filters.huella import huella
from collector.filters.pais import DESCONOCIDO, EXCLUIDO, pais_de_oferta
from collector.filters.titulo import FiltroTitulos
from collector.util.reloj import a_iso


def _fila(r: dict, cfg: Config, estado: str, motivo: Optional[str], pais: Optional[str], h: str, original: str) -> dict:
    return {
        "job_id": str(r["id"]), "url": r.get("url") or "", "titulo": r.get("title") or "",
        "empresa": r.get("company"), "ubicacion": r.get("location"), "pais": pais,
        "fecha_publicacion": r.get("date"), "modalidad": r.get("modalidad") or cfg.modalidad.busqueda.nombre,
        "estado": estado, "motivo_descarte": motivo, "huella": h, "duplicada_de": original or None,
    }


def _destino(cfg: Config, situacion: str, pais: Optional[str], original: str) -> Tuple[str, Optional[str]]:
    """(estado, motivo) de una oferta nueva según las reglas de ingreso de decisiones.md."""
    if situacion == EXCLUIDO:
        clave = "pais_excluido"
    elif original:
        clave = "duplicada"
    elif situacion == DESCONOCIDO:
        clave = "pais_desconocido"
    else:
        return PENDIENTE, None
    regla = cfg.decisiones.ingreso[clave]
    return (DESCARTADA if regla.accion == "descartar" else PENDIENTE), regla.motivo_para(pais, original)


def _por_modalidad(cfg: Config, modalidad: Optional[str], estado: str, motivo: Optional[str]) -> Tuple[str, Optional[str]]:
    """Una tarjeta con la etiqueta de otra modalidad no gasta una petición de detalle; si no, queda como estaba."""
    if not modalidad or modalidad in cfg.modalidad.aceptadas:
        return estado, motivo
    regla = cfg.decisiones.regla("modalidad_no_aceptada")
    return regla.estado, regla.motivo.format(modalidad=modalidad) if regla.motivo else None


def ingerir(con: sqlite3.Connection, cfg: Config, ubic: Ubicacion, consulta_id: int,
            resultados: List[dict], ahora: datetime) -> int:
    """Inserta lo nuevo, anota cada hallazgo y devuelve cuántas ofertas eran nuevas."""
    ahora_iso = a_iso(ahora)
    desde = a_iso(ahora - timedelta(days=cfg.lotes.entero("huella_dias")))
    filtro = FiltroTitulos(cfg.prefiltro)
    nuevas = 0
    for r in resultados:
        job_id = str(r["id"])
        if not ofertas_repo.existe(con, job_id):   # la que ya existe se omite: no se toca nada
            pais, situacion = pais_de_oferta(r.get("location"), cfg.paises_aceptados, cfg.paises_excluidos,
                                             ubic.pais_esperado)
            h = huella(r.get("company"), r.get("title"), r.get("location"))
            original = "" if situacion == EXCLUIDO else (ofertas_repo.buscar_original_por_huella(con, h, job_id, desde) or "")
            estado, motivo = _destino(cfg, situacion, pais, original)
            if estado == PENDIENTE:
                fuera = filtro.motivo_descarte(r.get("title") or "")
                estado, motivo = (DESCARTADA, fuera) if fuera else _por_modalidad(cfg, r.get("modalidad"), estado, motivo)
            ofertas_repo.insertar_nueva(con, _fila(r, cfg, estado, motivo, pais, h, original), ahora_iso)
            nuevas += 1
        consultas_repo.registrar_hallazgo(con, job_id, consulta_id)
    return nuevas


def descartar_por_titulo(con: sqlite3.Connection, cfg: Config) -> int:
    """Aplica el filtro de título a las ofertas que siguen pendientes de detalle (entraron con otras reglas o
    cambió prefiltro.md). No cuenta como detalle consumido. Devuelve cuántas descartó."""
    filtro = FiltroTitulos(cfg.prefiltro)
    descartadas = 0
    for o in ofertas_repo.pendientes_de_detalle(con):
        motivo = filtro.motivo_descarte(o["titulo"])
        if motivo:
            ofertas_repo.descartar(con, o["job_id"], motivo)
            descartadas += 1
    return descartadas


def por_descartar_por_titulo(con: sqlite3.Connection, cfg: Config) -> int:
    """Cuántas descartaría `descartar_por_titulo`, sin tocar nada (para los simulacros y `status`)."""
    filtro = FiltroTitulos(cfg.prefiltro)
    return sum(1 for o in ofertas_repo.pendientes_de_detalle(con) if filtro.motivo_descarte(o["titulo"]))
