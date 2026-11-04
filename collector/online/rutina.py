"""Lo que la Action comunica de la rutina, calculado con consultas a Neon (la rutina no escribe mensajes):
un aviso por cada oferta sin CV y, cuando la dispara la rutina, el resumen o «nada por redactar»."""
from __future__ import annotations

from typing import Dict, List

from collector.online import avisos, mensajes

_SIN_CV = """SELECT e.job_id, e.afinidad, e.motivo, o.empresa, o.titulo, o.url FROM emparejamientos e
             JOIN ofertas o ON o.job_id = e.job_id WHERE e.estado = 'sin_cv' AND e.notificado_en IS NULL
             ORDER BY e.emparejado_en"""
_QUEDAN = "SELECT job_id, empresa, titulo FROM ofertas_por_redactar ORDER BY intentos DESC, job_id"


def _filas(pg, sql: str, columnas, params=()) -> List[Dict]:
    cur = pg.cursor()
    cur.execute(sql, params)
    return [dict(zip(columnas, f)) for f in cur.fetchall()]


def encolar_sin_cv(pg, ahora: str) -> int:
    """Un aviso por oferta sin CV todavía no avisada; el aviso y la marca van en la misma transacción."""
    filas = _filas(pg, _SIN_CV, ("job_id", "afinidad", "motivo", "empresa", "titulo", "url"))
    for o in filas:
        avisos.encolar(pg, mensajes.sin_cv(o), "sin_cv")
        pg.cursor().execute("UPDATE emparejamientos SET notificado_en = %s WHERE job_id = %s", (ahora, o["job_id"]))
    pg.commit()
    return len(filas)


def _desde(pg) -> str:
    """Fin del resumen anterior: lo que la rutina registró después pertenece a esta ejecución."""
    cur = pg.cursor()
    cur.execute("SELECT MAX(creado_en) FROM avisos WHERE tipo = 'resumen'")
    return cur.fetchone()[0] or ""


def _contar(pg, condicion: str, desde: str) -> int:
    cur = pg.cursor()
    cur.execute(f"SELECT COUNT(*) FROM emparejamientos WHERE emparejado_en > %s AND {condicion}", (desde,))
    return cur.fetchone()[0]


def encolar_resumen(pg, dia: str) -> str:
    """Resumen de la ejecución de la rutina. Devuelve qué mensaje se encoló: resumen, nada o sin_registros."""
    desde = _desde(pg)
    redactados = _contar(pg, "estado <> 'sin_cv'", desde)
    correcciones = _contar(pg, "estado <> 'sin_cv' AND intentos > 0", desde)
    sin_cv = _contar(pg, "estado = 'sin_cv'", desde)
    quedan = _filas(pg, _QUEDAN, ("job_id", "empresa", "titulo"))
    if redactados or sin_cv:
        tipo, texto = "resumen", mensajes.resumen_rutina(dia, redactados, correcciones, sin_cv, quedan)
    elif not quedan:
        tipo, texto = "nada", mensajes.nada_por_redactar(dia)
    else:
        tipo, texto = "sin_registros", mensajes.rutina_sin_registros(dia, quedan)
    avisos.encolar(pg, texto, "resumen")   # cualquiera de los tres cierra la ventana del siguiente resumen
    pg.commit()
    return tipo
