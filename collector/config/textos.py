"""Carga y valida inputs/mensajes/*.md: ajustes y plantillas de Telegram. El código fija qué marcadores admite cada
plantilla (el vocabulario); el texto, las URL, la zona horaria y los emoji viven en el archivo."""
from __future__ import annotations

from pathlib import Path
from string import Formatter
from typing import Dict, Tuple

from collector.config.modelos import ConfigError, ConfigMensajes
from collector.util.md_tables import leer_tablas

_OFERTA = ("emoji", "cabecera", "job_id", "url")
CAMPOS: Dict[str, Tuple[str, ...]] = {
    "cv_listo": _OFERTA + ("lugar", "cv_id", "afinidad"),
    "sin_cv": _OFERTA + ("afinidad", "motivo"),
    "rechazo": _OFERTA + ("intento", "maximo", "motivo", "cierre", "consulta"),
    "rechazo_cierre_final": ("job_id",),
    "rechazo_cierre_reintento": (),
    "resumen_rutina": ("emoji", "dia", "redactados", "correcciones", "sin_cv", "quedan", "bloque"),
    "resumen_quedan": ("tope", "lista"),
    "nada_por_redactar": ("emoji", "dia"),
    "rutina_sin_registros": ("emoji", "dia", "quedan", "lista"),
    "captura": ("emoji", "dia", "motivo", "peticiones", "busquedas", "detalles", "nuevas", "aptas", "revisar",
                "descartadas", "subida", "revisar_bloque", "cierre"),
    "tanda_detalles": ("emoji", "dia", "procesadas", "aptas", "revisar", "descartadas", "detenida", "subida", "revisar_bloque"),
    "tanda_detenida": ("motivo",),
    "revisar_bloque": ("n", "resumen", "lista", "consulta"),
    "revisar_vineta": ("job_id", "cabecera", "motivo"),
    "vineta_oferta": ("job_id", "cabecera"),
    "vinetas_mas": ("n",),
    "consulta": ("sql", "url"),
    "sql_rechazo": ("job_id",),
    "fin_captura_rutina": ("url", "hora"),
    "fin_captura_apagado": ("hora",),
    "aviso_linkedin": ("emoji", "texto"),
    "linkedin_verificacion": ("url",),
    "linkedin_sesion_caducada": (),
    "alerta_captura": ("emoji", "titulo", "cuando", "datos"),
    "alerta_titulo_parada_total": (), "alerta_titulo_limite": (), "alerta_titulo_detenida": (),
    "alerta_titulo_subida": (), "alerta_titulo_tanda": (), "alerta_titulo_ctrl_c": (),
    "alerta_titulo_error": ("tipo",),
    "alerta_motivo": ("motivo",), "alerta_pausa": ("hasta",), "alerta_subida": ("subida",), "alerta_reintento": (), "alerta_apagado": ("hora",),
    "subida_sin_cambios": (), "subida_completa": (), "subida_no_configurada": ("variable",), "subida_fallida": ("n",),
}
CON_EMOJI = tuple(i for i, c in CAMPOS.items() if "emoji" in c)
AJUSTES = ("repo_github", "neon_project_id", "zona_horaria", "formato_fecha", "formato_hora", "formato_hora_corta", "url_consola_neon", "url_rutina", "hora_rutina",
           "presupuesto_vinetas", "prefijo_pdf", "sin_empresa", "sin_motivo") + tuple(f"emoji_{i}" for i in CON_EMOJI)
ENTEROS = ("presupuesto_vinetas",)


def _marcadores(plantilla: str) -> set:
    try:
        return {campo for _, campo, _, _ in Formatter().parse(plantilla) if campo is not None}
    except ValueError as e:
        raise ConfigError(f"mensajes/*.md: llaves mal cerradas en «{plantilla[:40]}» ({e})") from None


def _validar(ajustes: Dict[str, str], plantillas: Dict[str, str]) -> None:
    for clave in AJUSTES:
        if not ajustes.get(clave):
            raise ConfigError(f"mensajes/*.md: falta el ajuste «{clave}»")
    for clave in ENTEROS:
        if not ajustes[clave].isdigit():
            raise ConfigError(f"mensajes/*.md: el ajuste «{clave}» debe ser un entero, no «{ajustes[clave]}»")
    for id_, campos in CAMPOS.items():
        if id_ not in plantillas:
            raise ConfigError(f"mensajes/*.md: falta la plantilla «{id_}»")
        sobran = _marcadores(plantillas[id_]) - set(campos)
        if sobran:
            raise ConfigError(f"mensajes/*.md: la plantilla «{id_}» usa marcadores que no admite: {', '.join(sorted(sobran))}")
        if "job_id" in campos and id_ in ("cv_listo", "sin_cv", "rechazo") and "job_id" not in _marcadores(plantillas[id_]):
            raise ConfigError(f"mensajes/*.md: la plantilla «{id_}» debe llevar {{job_id}}")
    desconocidas = set(plantillas) - set(CAMPOS)
    if desconocidas:
        raise ConfigError(f"mensajes/*.md: plantillas que el código no usa: {', '.join(sorted(desconocidas))}")


ARCHIVOS = ("parametros.md", "enlaces.md", "emoji.md", "plantillas_cv.md", "plantillas_captura.md")


def _fusionar(destino: Dict[str, str], nuevo: Dict[str, str], archivo: str) -> None:
    repetidas = set(destino) & set(nuevo)
    if repetidas:
        raise ConfigError(f"mensajes/{archivo}: claves ya definidas en otro archivo: {', '.join(sorted(repetidas))}")
    destino.update(nuevo)


def cargar(carpeta) -> ConfigMensajes:
    """Lee `inputs/mensajes/*.md`: parámetros, enlaces, emoji y plantillas, cada naturaleza en su archivo."""
    ajustes: Dict[str, str] = {}
    plantillas: Dict[str, str] = {}
    for archivo in ARCHIVOS:
        ruta = Path(carpeta) / "mensajes" / archivo
        if not ruta.exists():
            raise ConfigError(f"falta el archivo de parámetros {ruta}")
        tablas = leer_tablas(ruta)
        _fusionar(ajustes, {f["clave"]: f["valor"] for f in tablas.get("ajustes", [])}, archivo)
        _fusionar(plantillas, {f["id"]: f["plantilla"].replace("\\n", "\n") for f in tablas.get("mensajes", [])}, archivo)
    _validar(ajustes, plantillas)
    return ConfigMensajes(ajustes, plantillas)
