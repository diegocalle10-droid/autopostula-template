"""Pide el detalle de las ofertas elegibles y las evalúa (idioma, modalidad, keywords, decisión)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from collector.config.modelos import Config
from collector.db import eventos_repo, ofertas_repo
from collector.db.connection import transaccion
from collector.filters.evaluar import evaluar
from collector.linkedin.errores import LimiteError, LinkedinError, NoEncontradaError
from collector.pipeline import breaker, seleccion
from collector.pipeline.ritmo import Ritmo
from collector.util.reloj import a_iso

FALLOS_DE_OFERTA = ("DESCRIPCION_VACIA", "OFERTA_SIN_CONTENIDO")   # la página de esa oferta, no la sesión ni la red


@dataclass
class ResultadoDetalle:
    procesadas: int = 0
    aptas: int = 0
    revisar: int = 0
    descartadas: int = 0
    ilegibles: int = 0       # descartadas porque su detalle llegó sin contenido varias veces
    limite: bool = False
    detenida_por: Optional[str] = None


def _pedir(cli, job_id: str) -> dict:
    """El detalle de una oferta; una descripción vacía (p. ej. una página de desafío con HTTP 200) es un fallo."""
    detalle = cli.detalle(job_id)
    if not (detalle.get("description") or "").strip():
        raise LinkedinError("DESCRIPCION_VACIA", "el detalle no trae descripción")
    return detalle


def _fallo(con: sqlite3.Connection, cfg: Config, job_id: str, error: LinkedinError, ahora_iso: str) -> bool:
    """Registra el fallo. Si es de la oferta (no de la sesión ni de la red) y ya se repitió `fallos_por_oferta_para_descartar`
    veces, la descarta para no bloquear la cola: True."""
    with transaccion(con):
        eventos_repo.registrar(con, "fallo", ahora_iso, f"detail {job_id}: {error.codigo}")
        if error.codigo not in FALLOS_DE_OFERTA or                 eventos_repo.contar_fallos_oferta(con, job_id) < cfg.lotes.entero("fallos_por_oferta_para_descartar"):
            return False
        ofertas_repo.descartar(con, job_id, cfg.decisiones.regla("detalle_ilegible").motivo, ahora_iso)
    return True


def _guardar(con: sqlite3.Connection, cfg: Config, oferta, detalle: dict, ahora_iso: str) -> str:
    pais_desconocido = oferta["motivo_descarte"] == cfg.decisiones.ingreso["pais_desconocido"].motivo_para(None, "")
    activa = bool(detalle.get("isActive", True))
    ev = evaluar(oferta["titulo"], detalle["description"], activa, cfg, pais_desconocido, detalle.get("modalidad"))
    datos = {
        "descripcion": detalle["description"], "tipo_empleo": detalle.get("employmentType"), "activa": int(activa),
        "modalidad_detectada": ev.modalidad_detectada, "idioma_titulo": ev.idioma_titulo,
        "idioma_contenido": ev.idioma_contenido, "nivel_idioma": ev.nivel_idioma,
        "estado": ev.estado, "motivo_descarte": ev.motivo_descarte,
    }
    with transaccion(con):
        ofertas_repo.guardar_evaluacion(con, oferta["job_id"], datos, ev.keywords, ahora_iso)
    return ev.estado


def procesar_detalles(con: sqlite3.Connection, cfg: Config, cli, ritmo: Ritmo,
                      reloj: Callable[[], datetime], max_ofertas: int) -> ResultadoDetalle:
    res = ResultadoDetalle()
    ok, razon = breaker.puede_ejecutar(con, cfg, reloj())
    if not ok:
        res.detenida_por = razon
        return res
    elegidas = seleccion.seleccionar(ofertas_repo.pendientes_de_detalle(con), cfg,
                                     max_ofertas)
    fallos, maximo = 0, cfg.lotes.entero("fallos_seguidos_para_parada")
    for oferta in (e.oferta for e in elegidas.elegibles):
        ahora = reloj()
        ritmo.esperar()
        try:
            detalle = _pedir(cli, oferta["job_id"])
        except NoEncontradaError:
            with transaccion(con):
                ofertas_repo.descartar(con, oferta["job_id"], cfg.decisiones.regla("cerrada").motivo, a_iso(ahora))
            res.procesadas, res.descartadas, fallos = res.procesadas + 1, res.descartadas + 1, 0
            continue
        except LimiteError:
            res.limite, res.detenida_por = True, breaker.parar_por_limite(con, cfg, ahora, f"detail {oferta['job_id']}")
            break
        except LinkedinError as e:
            if _fallo(con, cfg, oferta["job_id"], e, a_iso(ahora)):
                res.procesadas, res.descartadas, res.ilegibles = res.procesadas + 1, res.descartadas + 1, res.ilegibles + 1
            fallos += 1
            if fallos >= maximo:
                with transaccion(con):
                    breaker.parar_por_fallos(con, cfg, ahora, f"{maximo} fallos seguidos en el detalle")
                res.detenida_por = "fallos seguidos en el detalle"
                break
            continue
        fallos = 0
        estado = _guardar(con, cfg, oferta, detalle, a_iso(ahora))
        res.procesadas += 1
        res.aptas, res.revisar, res.descartadas = (res.aptas + (estado == "apta"), res.revisar + (estado == "revisar"),
                                                   res.descartadas + (estado == "descartada"))
    return res
