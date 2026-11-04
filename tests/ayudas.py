"""Utilidades de prueba: configuración real, base en memoria, CLI de LinkedIn simulado y reloj fijo."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from collector.config.cargar import cargar_config
from collector.db.connection import conectar
from collector.db.migrar import migrar
from collector.linkedin.errores import NoEncontradaError
from collector.online import mensajes
from collector.pipeline.ritmo import Ritmo

PROYECTO = Path(__file__).resolve().parent.parent
RAIZ = PROYECTO / "tests" / "fixtures"   # inputs/ y CV/base/ de ejemplo: las pruebas no dependen de los datos del usuario
mensajes._RAIZ_INPUTS = RAIZ / "inputs"   # también los textos de Telegram por defecto


def obtener_combinacion(con, combinacion_id):
    return con.execute("SELECT * FROM combinaciones WHERE combinacion_id = ?", (combinacion_id,)).fetchone()


def config():
    return cargar_config(RAIZ / "inputs")


def base_en_memoria():
    con = conectar(":memory:")
    migrar(con)
    return con


def reloj_fijo(dia: int = 28, hora: int = 12):
    """Un reloj que siempre marca las `hora`:00 locales del día `dia` de octubre de 2026."""
    instante = datetime(2026, 10, dia, hora, 0).astimezone()
    return lambda: instante


def cv_derivado(nombre: str = "data_analytics") -> str:
    """El CV base real con las rayas largas de los logros cambiadas por comas: lo que entregaría una rutina sin errores."""
    salida, en_logros = [], True
    for linea in (RAIZ / "CV" / "base" / f"{nombre}.md").read_text(encoding="utf-8").splitlines():
        en_logros = en_logros and not linea.startswith("## FORMACI")
        salida.append(linea.replace(" — ", ", ").replace("—", ",") if en_logros and linea.startswith("- ") else linea)
    return "\n".join(salida) + "\n"


DESCRIPCION = {"description": "Puesto 100% remoto. Buscamos analista de datos con SQL y Power BI.", "isActive": True}


class RelojSimulado:
    """El tiempo avanza solo cuando el flujo duerme."""

    def __init__(self):
        self.t = datetime(2026, 10, 28, 12, 0).astimezone()
        self.pausas = []

    def ahora(self):
        return self.t

    def dormir(self, segundos):
        self.pausas.append(segundos)
        self.t += timedelta(seconds=segundos)


def sin_pausas() -> Ritmo:
    """Un ritmo que no duerme nunca."""
    return Ritmo(10 ** 9, (0, 0), (0, 0), dormir=lambda s: None)


def oferta(job_id, titulo="Analista de datos", empresa="Acme", ubicacion="Mexico City, Mexico", fecha="2026-10-20"):
    return {"id": str(job_id), "title": titulo, "company": empresa, "location": ubicacion, "date": fecha,
            "url": f"https://www.linkedin.com/jobs/view/{job_id}"}


class CliFalso:
    """Imita a LinkedinSesion. `guion` es una lista de respuestas (listas de ofertas) o excepciones, en orden."""

    def __init__(self, guion=None, detalles=None):
        self.guion = list(guion or [])
        self.detalles = detalles or {}
        self.llamadas = []

    def buscar(self, termino, ubicacion, jobage, flag, pagina):
        self.llamadas.append(("buscar", termino, ubicacion, jobage, flag, pagina))
        if not self.guion:
            return []
        paso = self.guion.pop(0)
        if isinstance(paso, Exception):
            raise paso
        return paso

    def detalle(self, job_id):
        self.llamadas.append(("detalle", job_id))
        d = self.detalles.get(str(job_id))
        if isinstance(d, Exception):
            raise d
        if d is None:
            raise NoEncontradaError("NOT_FOUND", "Job not found")
        return d
