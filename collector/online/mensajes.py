"""Mensajes de Telegram. Los textos, las URL, la zona horaria y los emoji viven en `inputs/mensajes/`; aquí solo se
escapan los datos y se rellenan los marcadores (HTML de Telegram: solo <b> y <code>). Cada mensaje de una oferta lleva el
job_id en su propia línea; las listas, en cada viñeta."""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from collector.config import textos
from collector.config.modelos import ConfigMensajes
from collector.online import consultas

Fila = Dict[str, object]
_RAIZ_INPUTS = Path(__file__).resolve().parents[2] / "inputs"
_catalogo: Optional[ConfigMensajes] = None


class Html(str):
    """Texto ya escapado o plantilla de confianza: `texto()` no vuelve a escaparlo."""


def usar(catalogo: Optional[ConfigMensajes]) -> None:
    """Cambia el catálogo (pruebas, o `--inputs` distinto). None = volver al de inputs/ del proyecto."""
    global _catalogo
    _catalogo = catalogo


def _cat() -> ConfigMensajes:
    global _catalogo
    if _catalogo is None:
        _catalogo = textos.cargar(_RAIZ_INPUTS)
    return _catalogo


def ajuste(clave: str) -> str:
    return _cat().ajustes[clave]


def _e(valor: object, largo: int = 160) -> Html:
    texto = "" if valor is None else str(valor)
    return Html(html.escape(texto if len(texto) <= largo else texto[:largo - 1] + "…", quote=False))


def texto(id_: str, **campos: object) -> Html:
    """Rellena la plantilla `id_`. Lo que no es `Html` se escapa; el emoji de la plantilla sale de los ajustes."""
    if "emoji" in textos.CAMPOS[id_]:
        campos["emoji"] = Html(ajuste(f"emoji_{id_}"))
    return Html(_cat().plantillas[id_].format_map({k: v if isinstance(v, Html) else _e(v) for k, v in campos.items()}))


def fecha(instante: datetime) -> str:
    return instante.astimezone(ZoneInfo(ajuste("zona_horaria"))).strftime(ajuste("formato_fecha"))


def hora(instante: datetime) -> str:
    return instante.astimezone(ZoneInfo(ajuste("zona_horaria"))).strftime(ajuste("formato_hora"))


def hora_corta(instante: datetime) -> str:
    return instante.astimezone(ZoneInfo(ajuste("zona_horaria"))).strftime(ajuste("formato_hora_corta"))


def fin_captura_apagado(hora_apagado: str) -> str:
    return texto("alerta_apagado", hora=hora_apagado)


def _cabecera(o: Fila) -> Html:
    return Html(f"{_e(o.get('empresa') or ajuste('sin_empresa'), 80)} · {_e(o.get('titulo'), 120)}")


def _lista(lineas: List[str]) -> Html:
    """Las viñetas que quepan en el presupuesto; el resto se resume en «… y N más» (cortar HTML a mitad rompe el mensaje)."""
    presupuesto, salida, usado = int(ajuste("presupuesto_vinetas")), [], 0
    for i, linea in enumerate(lineas):
        if usado + len(linea) > presupuesto:
            salida.append(texto("vinetas_mas", n=len(lineas) - i))
            break
        salida.append(linea)
        usado += len(linea) + 1
    return Html("\n".join(salida))


def _vinetas_ofertas(ofertas: List[Fila]) -> Html:
    return _lista([texto("vineta_oferta", job_id=o["job_id"], cabecera=_cabecera(o)) for o in ofertas])


def _consulta(sql: str) -> Html:
    return texto("consulta", sql=Html(html.escape(sql, quote=False)), url=ajuste("url_consola_neon"))


def cv_listo(o: Fila) -> str:
    """Pie del PDF (Telegram admite 1.024 caracteres visibles)."""
    lugar = " · ".join(_e(v, 60) for v in (o.get("ubicacion"), o.get("modalidad")) if v)
    return texto("cv_listo", cabecera=_cabecera(o), job_id=o["job_id"], lugar=Html(lugar + " · " if lugar else ""),
                 cv_id=o.get("cv_id"), afinidad=o.get("afinidad"), url=_e(o.get("url"), 300))


def sin_cv(o: Fila) -> str:
    afinidad = o.get("afinidad") if o.get("afinidad") is not None else "?"
    return texto("sin_cv", cabecera=_cabecera(o), job_id=o["job_id"], afinidad=afinidad, motivo=_e(o.get("motivo"), 300),
                 url=_e(o.get("url"), 300))


def rechazo(o: Fila, intento: int, maximo: int, motivo: str) -> str:
    cierre = texto("rechazo_cierre_final" if intento >= maximo else "rechazo_cierre_reintento", job_id=o["job_id"])
    return texto("rechazo", cabecera=_cabecera(o), job_id=o["job_id"], intento=intento, maximo=maximo,
                 motivo=_e(motivo, 600), url=_e(o.get("url"), 300), cierre=cierre, consulta=_consulta(texto("sql_rechazo", job_id=o["job_id"])))


def resumen_rutina(dia: str, redactados: int, correcciones: int, sin_cv_n: int, quedan: List[Fila], tope: int) -> str:
    bloque = texto("resumen_quedan", tope=tope, lista=_vinetas_ofertas(quedan)) if quedan else ""
    return texto("resumen_rutina", dia=dia, redactados=redactados, correcciones=correcciones, sin_cv=sin_cv_n,
                 quedan=len(quedan), bloque=Html(bloque))


def nada_por_redactar(dia: str) -> str:
    return texto("nada_por_redactar", dia=dia)


def rutina_sin_registros(dia: str, quedan: List[Fila]) -> str:
    return texto("rutina_sin_registros", dia=dia, quedan=len(quedan), lista=_vinetas_ofertas(quedan))


def _revisar_bloque(revisar: Optional[List[Fila]]) -> Html:
    """Las ofertas por revisar, resumidas por motivo y con la consulta para verlas en Neon; vacío si no hay ninguna."""
    if not revisar:
        return Html("")
    motivos: Dict[str, int] = {}
    for o in revisar:
        m = str(o.get("motivo_descarte") or ajuste("sin_motivo"))
        motivos[m] = motivos.get(m, 0) + 1
    resumen = ", ".join(f"{_e(m)} {n}" for m, n in sorted(motivos.items(), key=lambda x: -x[1]))
    lista = _lista([texto("revisar_vineta", job_id=o["job_id"], cabecera=_cabecera(o),
                          motivo=o.get("motivo_descarte") or ajuste("sin_motivo")) for o in revisar])
    return texto("revisar_bloque", n=len(revisar), resumen=Html(resumen), lista=lista, consulta=_consulta(consultas.REVISAR_SQL))


def captura(dia: str, motivo: str, r, subida: str, revisar: Optional[List[Fila]], cierre: str = "") -> str:
    return texto("captura", dia=dia, motivo=motivo, peticiones=len(r.secuencia), busquedas=r.busquedas,
                 detalles=r.secuencia.count("D"), nuevas=r.nuevas, aptas=r.aptas, revisar=r.revisar,
                 descartadas=r.descartadas, subida=subida, revisar_bloque=_revisar_bloque(revisar), cierre=Html(cierre))


def fin_captura(hora_apagado: Optional[str]) -> str:
    """Cierre del resumen de la captura: cómo lanzar la rutina de CV y, si está activado, cuándo se apaga el PC."""
    cierre = texto("fin_captura_rutina", url=Html(ajuste("url_rutina")), hora=ajuste("hora_rutina"))
    return cierre + (texto("fin_captura_apagado", hora=hora_apagado) if hora_apagado else "")


def tanda_detalles(dia: str, r, subida: str, revisar: Optional[List[Fila]]) -> str:
    """Resumen de una tanda manual de detalles (comando `detail`)."""
    detenida = texto("tanda_detenida", motivo=r.detenida_por) if r.detenida_por else ""
    return texto("tanda_detalles", dia=dia, procesadas=r.procesadas, aptas=r.aptas, revisar=r.revisar,
                 descartadas=r.descartadas, detenida=Html(detenida), subida=subida, revisar_bloque=_revisar_bloque(revisar))


def aviso_linkedin(clave: str, **datos: object) -> str:
    """`clave` es un id `linkedin_*`; sus datos se escapan (quien llama los acorta)."""
    return texto("aviso_linkedin", texto=texto(clave, **datos))


def linea(id_: str, **campos: object) -> str:
    """Una línea de datos de una alerta o un título (`alerta_*`, `subida_*`)."""
    return texto(id_, **campos)


def alerta_captura(titulo: str, cuando: str, datos: Iterable[str]) -> str:
    return texto("alerta_captura", titulo=titulo, cuando=cuando, datos=Html("\n".join(d if isinstance(d, Html) else _e(d, 300) for d in datos)))
