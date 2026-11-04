"""Validación y PDF de los CV que redactó la rutina (estado `redactada` en Neon). Lo ejecuta GitHub Actions, sin IA.
Pasa las reglas de siempre (collector/filters) contra el CV base. Si falla: `rechazada` con el motivo y un intento más;
la rutina lo reescribe mientras `intentos` < 3, y se avisa en el 1.º y el 3.º. Si pasa: PDF de máximo 2 páginas,
sin marcas, `validada`, y se envía por Telegram con su pie."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional

from collector.cv.render import MAX_PAGINAS, generar_pdf
from collector.filters.cv import nombre_pdf, problemas, quitar_marcadores, slug
from collector.filters.cv_datos import verificar_datos
from collector.online import avisos, mensajes

# Las validadas sin avisar vuelven a pasar: el PDF se regenera y el aviso se reintenta.
_COLUMNAS = ("job_id", "cv_id", "cv_md", "afinidad", "intentos", "empresa", "titulo", "url", "ubicacion", "modalidad")
_PENDIENTES = """SELECT e.job_id, e.cv_id, e.cv_md, e.afinidad, e.intentos, o.empresa, o.titulo, o.url, o.ubicacion, o.modalidad
                 FROM emparejamientos e JOIN ofertas o ON o.job_id = e.job_id
                 WHERE e.estado = 'redactada' OR (e.estado = 'validada' AND e.notificado_en IS NULL)
                 ORDER BY e.emparejado_en LIMIT %s"""
INTENTOS_CON_AVISO = (1, 3)
Enviar = Callable[[Path, str], None]


def motivo_rechazo(cfg, raiz: Path, cv_id: str, markdown: str) -> str:
    """'' si el CV es válido; si no, lo que hay que corregir."""
    base = cfg.cv.cv(cv_id or "")
    if base is None:
        return f"CV base desconocido «{cv_id}»"
    archivo = Path(raiz) / base.archivo
    if not archivo.is_file():
        return f"no existe el CV base {base.archivo}"
    return "; ".join(problemas(markdown) + verificar_datos(archivo.read_text(encoding="utf-8"), markdown))


def _rechazar(pg, o: Dict, motivo: str) -> None:
    """Rechazo y, si toca, su aviso en la misma transacción: no se pierde uno sin el otro."""
    intento = (o["intentos"] or 0) + 1
    pg.cursor().execute("UPDATE emparejamientos SET estado = 'rechazada', rechazo = %s, intentos = %s WHERE job_id = %s",
                        (motivo[:1000], intento, o["job_id"]))
    if intento in INTENTOS_CON_AVISO:
        avisos.encolar(pg, mensajes.rechazo(o, intento, motivo), "rechazo")
    pg.commit()


def _validar(pg, job_id: str, ahora: str) -> None:
    pg.cursor().execute("UPDATE emparejamientos SET estado = 'validada', rechazo = NULL, validado_en = COALESCE(validado_en, %s) WHERE job_id = %s",
                        (ahora, job_id))
    pg.commit()


def _avisar(pg, o: Dict, ahora: str, pdf: Path, enviar: Enviar, log) -> bool:
    try:
        enviar(pdf, mensajes.cv_listo(o))
    except Exception as e:   # el CV sigue validado y sin avisar: la próxima pasada reintenta
        log(f"AVISO FALLIDO {o['job_id']}: {e}")
        return False
    pg.cursor().execute("UPDATE emparejamientos SET notificado_en = %s WHERE job_id = %s", (ahora, o["job_id"]))
    pg.commit()
    return True


def _pdf(o: Dict, salida: Path) -> tuple:
    """(ruta, motivo de rechazo por páginas o '')."""
    destino = Path(salida) / f"{o['job_id']}_{slug(o['empresa'] or '')}" / nombre_pdf(mensajes.ajuste("prefijo_pdf"), o["titulo"])
    paginas, _ = generar_pdf(quitar_marcadores(o["cv_md"]), destino, f"CV {o['titulo']}")
    return destino, (f"ocupa {paginas} páginas (máximo {MAX_PAGINAS})" if paginas > MAX_PAGINAS else "")


def procesar(pg, cfg, raiz: Path, salida: Path, ahora: str, maximo: int = 50,
             log: Callable[[str], None] = print, enviar: Optional[Enviar] = None) -> Dict[str, List[str]]:
    """Devuelve los job_id `validadas`, `rechazadas` y `avisadas` de esta pasada. Con `enviar`, avisa de cada validada."""
    cur = pg.cursor()
    cur.execute(_PENDIENTES, (maximo,))
    res: Dict[str, List[str]] = {"validadas": [], "rechazadas": [], "avisadas": []}
    for o in (dict(zip(_COLUMNAS, f)) for f in cur.fetchall()):
        motivo, destino = motivo_rechazo(cfg, raiz, o["cv_id"], o["cv_md"]), None
        if not motivo:
            destino, motivo = _pdf(o, salida)
        if motivo:
            _rechazar(pg, o, motivo)
            res["rechazadas"].append(o["job_id"])
            log(f"RECHAZADA {o['job_id']}: {motivo}")
            continue
        _validar(pg, o["job_id"], ahora)
        res["validadas"].append(o["job_id"])
        log(f"OK        {o['job_id']}: PDF listo")
        if enviar and _avisar(pg, o, ahora, destino, enviar, log):
            res["avisadas"].append(o["job_id"])
    return res
