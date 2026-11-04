"""Carga y valida inputs/*.md. Nada de lo que se busca ni de lo que se decide está escrito en el código."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, FrozenSet, List, Sequence, Tuple

from collector.config.modelos import (
    Config, ConfigCv, ConfigDecisiones, ConfigError, ConfigIdioma, ConfigModalidad, ConfigPrefiltro, CvBase, Escalon429,
    FamiliaTitulo,
    Lotes, Modalidad, ReglaDecision, ReglaIngreso, Termino, Ubicacion,
)
from collector.config import textos
from collector.estados import CONDICIONES, ESTADOS_DE_DECISION
from collector.util.md_tables import leer_tablas
from collector.util.texto import normalizar, patron

CLAVES_LOTES = (
    "consultas_por_lote", "pausa_entre_consultas_min",
    "pausa_entre_consultas_max", "pausa_entre_lotes_min", "pausa_entre_lotes_max", "jobage_dias_primer_barrido",
    "max_paginas", "umbral_pagina_nuevas", "umbral_pagina_perfil", "margen_jobage_dias", "reintento_fallida_horas", "detail_por_lote", "detalles_pendientes_max",
    "pausa_entre_detail_min", "pausa_entre_detail_max", "pausa_entre_lotes_detail_min",
    "pausa_entre_lotes_detail_max", "horas_por_defecto", "bloqueo_caduca_horas", "apagar_tras_captura_min",
    "vacios_seguidos_para_alerta", "pausa_tras_vacios_horas", "fallos_seguidos_para_parada", "fallos_por_oferta_para_descartar",
    "pausa_tras_fallos_horas", "ubicacion_sin_resultados_terminos", "ubicacion_sin_resultados_prioridad_max",
    "pasadas_sin_nuevas_para_duplicar", "factor_cadencia_poda", "cadencia_maxima_dias", "huella_dias",
)
ACCIONES_429 = ("pausa", "hasta_manana", "parada_total")
SITUACIONES_INGRESO = ("pais_excluido", "duplicada", "pais_desconocido")
CRITERIOS_ORDEN = ("prioridad_pais", "puntos", "recencia")


def _entero(valor: str, que: str) -> int:
    try:
        return int(valor)
    except ValueError:
        raise ConfigError(f"{que} debe ser un entero, no «{valor}»") from None


def _decimal(valor: str, que: str) -> float:
    try:
        return float(valor)
    except ValueError:
        raise ConfigError(f"{que} debe ser un número, no «{valor}»") from None


def _tabla(tablas: dict, seccion: str, archivo: str, columnas: Sequence[str]) -> List[Dict[str, str]]:
    filas = tablas.get(seccion)
    if not filas:
        raise ConfigError(f"{archivo}: falta la tabla «{seccion}» o está vacía")
    for c in columnas:
        if c not in filas[0]:
            raise ConfigError(f"{archivo}: la tabla «{seccion}» no tiene la columna «{c}»")
    return filas


def _reglas(tablas: dict, archivo: str, claves: Sequence[str]) -> Dict[str, str]:
    """La tabla «Reglas» de un archivo como {clave: valor}; falla si falta alguna de `claves`."""
    reglas = {f["clave"]: f["valor"] for f in _tabla(tablas, "reglas", archivo, ("clave", "valor"))}
    for c in claves:
        if c not in reglas:
            raise ConfigError(f"{archivo}: falta la regla «{c}»")
    return reglas


def _archivo(carpeta: Path, nombre: str) -> dict:
    ruta = carpeta / nombre
    if not ruta.exists():
        raise ConfigError(f"falta el archivo de parámetros {ruta}")
    return leer_tablas(ruta)


def _sin_guion_inicial(textos: Sequence[str], archivo: str) -> None:
    """Un texto que empieza por «-» se leería como un flag del CLI de búsqueda."""
    for t in textos:
        if t.startswith("-"):
            raise ConfigError(f"{archivo}: «{t}» no puede empezar por «-»")


def _ubicaciones(carpeta: Path):
    t = _archivo(carpeta, "ubicaciones.md")
    activas: List[Ubicacion] = []
    for seccion in (s for s in ("lugares", "paises", "regiones") if t.get(s)):
        for f in _tabla(t, seccion, "ubicaciones.md", ("tipo", "frase", "pais_esperado")):
            esperado = None if f["pais_esperado"] in ("", "-") else f["pais_esperado"]
            activas.append(Ubicacion(f["tipo"], f["frase"], esperado))
    if not activas:
        raise ConfigError("ubicaciones.md: la tabla «Lugares» está vacía; añade al menos un lugar donde buscar")
    filas = _tabla(t, "paises_aceptados", "ubicaciones.md", ("pais", "prioridad_detalle"))
    prioridad_pais = {f["pais"]: _entero(f["prioridad_detalle"], f"ubicaciones.md: prioridad_detalle de {f['pais']}")
                      for f in filas}
    excluidos = frozenset(f["pais"] for f in t.get("paises_excluidos", []))   # tabla opcional
    _sin_guion_inicial([u.frase for u in activas], "ubicaciones.md")
    return activas, frozenset(prioridad_pais), excluidos, prioridad_pais


def _terminos(carpeta: Path) -> List[Termino]:
    filas = _tabla(_archivo(carpeta, "puestos.md"), "terminos", "puestos.md", ("prioridad", "termino"))
    salida = [Termino(_entero(f["prioridad"], f"puestos.md: prioridad de «{f['termino']}»"), f["termino"]) for f in filas]
    _sin_guion_inicial([t.termino for t in salida], "puestos.md")
    return salida


def _modalidad(carpeta: Path) -> ConfigModalidad:
    t = _archivo(carpeta, "modalidades.md")
    mods = tuple(Modalidad(f["nombre"], f["filtro"], f["aceptada"] == "si",
                           tuple(normalizar(e) for e in f["etiquetas"].split(",") if e.strip()))
                 for f in _tabla(t, "modalidades", "modalidades.md", ("nombre", "filtro", "aceptada", "etiquetas")))
    if not any(m.aceptada for m in mods):
        raise ConfigError("modalidades.md: ninguna modalidad está marcada como aceptada")
    if any(not m.etiquetas for m in mods):
        raise ConfigError("modalidades.md: cada modalidad necesita al menos una etiqueta")
    return ConfigModalidad(mods)


def _palabras(filas: List[Dict[str, str]], archivo: str, codigos: Sequence[str]) -> Dict[str, FrozenSet[str]]:
    por_codigo = {f["idioma"]: frozenset(normalizar(p) for p in f["palabras"].split(",") if p.strip()) for f in filas}
    for c in codigos:
        if c not in por_codigo:
            raise ConfigError(f"{archivo}: falta la fila del idioma «{c}»")
    return por_codigo


def _idioma(carpeta: Path) -> ConfigIdioma:
    t = _archivo(carpeta, "idioma.md")
    r = _reglas(t, "idioma.md", ("ventana_mcer_chars", "ventana_negacion_chars", "umbral_idioma_dominante",
                                "minimo_palabras_detectadas", "idioma_propio", "idioma_vigilado"))
    codigos = (r["idioma_propio"], r["idioma_vigilado"])
    pal = _palabras(_tabla(t, "palabras_de_idioma", "idioma.md", ("idioma", "palabras")), "idioma.md", codigos)
    tit = _palabras(_tabla(t, "palabras_de_titulo", "idioma.md", ("idioma", "palabras")), "idioma.md", codigos)
    mcer = {normalizar(f["nivel"]): f["clase"] for f in _tabla(t, "niveles_mcer", "idioma.md", ("nivel", "clase"))}
    return ConfigIdioma(
        pasa=tuple(f["expresion"] for f in _tabla(t, "pasa", "idioma.md", ("expresion",))),
        rechaza=tuple(f["expresion"] for f in _tabla(t, "rechaza", "idioma.md", ("expresion",))),
        mcer=mcer,
        negaciones=tuple(f["expresion"] for f in _tabla(t, "negaciones", "idioma.md", ("expresion",))),
        ventana_mcer=_entero(r["ventana_mcer_chars"], "idioma.md: ventana_mcer_chars"),
        ventana_negacion=_entero(r["ventana_negacion_chars"], "idioma.md: ventana_negacion_chars"),
        umbral=_decimal(r["umbral_idioma_dominante"], "idioma.md: umbral_idioma_dominante"),
        minimo_palabras=_entero(r["minimo_palabras_detectadas"], "idioma.md: minimo_palabras_detectadas"),
        propio=codigos[0], vigilado=codigos[1],
        alias_vigilado=tuple(f["alias"] for f in _tabla(t, "alias_del_idioma_vigilado", "idioma.md", ("alias",))),
        palabras=pal, palabras_titulo=tit,
    )


def _lotes(carpeta: Path):
    t = _archivo(carpeta, "lotes.md")
    valores = {f["clave"]: f["valor"] for filas in t.values() for f in filas if "clave" in f and "valor" in f}
    lotes = Lotes(valores)
    for clave in CLAVES_LOTES:
        lotes.texto(clave)
    cad = _tabla(t, "cadencia_de_mantenimiento", "lotes.md", ("prioridad", "cadencia_dias"))
    cadencias = {_entero(f["prioridad"], "lotes.md: prioridad de la cadencia"):
                 _entero(f["cadencia_dias"], "lotes.md: cadencia_dias") for f in cad}
    return lotes, cadencias, _escalada_429(t)


def _escalada_429(t: dict) -> Tuple[Escalon429, ...]:
    escalones = []
    for f in _tabla(t, "escalada_del_429", "lotes.md", ("ocurrencias", "ventana_dias", "accion", "horas")):
        if f["accion"] not in ACCIONES_429:
            raise ConfigError(f"lotes.md: acción de escalada desconocida «{f['accion']}» (válidas: {', '.join(ACCIONES_429)})")
        horas = None if f["horas"] in ("", "-") else _entero(f["horas"], "lotes.md: horas de la escalada")
        if f["accion"] != "hasta_manana" and horas is None:
            raise ConfigError(f"lotes.md: la acción «{f['accion']}» necesita «horas»")
        escalones.append(Escalon429(_entero(f["ocurrencias"], "lotes.md: ocurrencias"),
                                    _entero(f["ventana_dias"], "lotes.md: ventana_dias"), f["accion"], horas))
    if not any(e.ocurrencias == 1 for e in escalones):
        raise ConfigError("lotes.md: la escalada del 429 necesita un escalón con ocurrencias = 1")
    return tuple(sorted(escalones, key=lambda e: -e.ocurrencias))


def _decisiones(carpeta: Path) -> ConfigDecisiones:
    t = _archivo(carpeta, "decisiones.md")
    reglas = []
    for f in _tabla(t, "reglas_de_decision", "decisiones.md", ("condicion", "estado", "motivo")):
        if f["condicion"] not in CONDICIONES:
            raise ConfigError(f"decisiones.md: condición desconocida «{f['condicion']}»")
        if f["estado"] not in ESTADOS_DE_DECISION:
            raise ConfigError(f"decisiones.md: estado desconocido «{f['estado']}» en «{f['condicion']}»")
        if f["estado"] == "descartada" and not f["motivo"]:
            raise ConfigError(f"decisiones.md: la regla «{f['condicion']}» descarta y necesita motivo")
        try:
            f["motivo"].format(modalidad="x")
        except (KeyError, IndexError, ValueError):
            raise ConfigError(f"decisiones.md: motivo inválido en «{f['condicion']}» (solo admite {{modalidad}})") from None
        reglas.append(ReglaDecision(f["condicion"], f["estado"], f["motivo"] or None))
    if not {"cerrada", "detalle_ilegible"} <= {r.condicion for r in reglas} or reglas[-1].condicion != "siempre":
        raise ConfigError("decisiones.md: deben existir las reglas «cerrada» y «detalle_ilegible», y la última tiene que ser «siempre»")
    return ConfigDecisiones(tuple(reglas), _ingreso(t))


def _ingreso(t: dict) -> Dict[str, ReglaIngreso]:
    ingreso = {}
    for f in _tabla(t, "reglas_de_ingreso", "decisiones.md", ("situacion", "accion", "motivo")):
        if f["situacion"] not in SITUACIONES_INGRESO:
            raise ConfigError(f"decisiones.md: situación de ingreso desconocida «{f['situacion']}»")
        validas = ("descartar", "esperar", "evaluar") if f["situacion"] == "pais_desconocido" else ("descartar",)
        if f["accion"] not in validas:
            raise ConfigError(f"decisiones.md: «{f['situacion']}» solo admite {', '.join(validas)}")
        try:
            f["motivo"].format(pais="x", original="x")
        except (KeyError, IndexError, ValueError):
            raise ConfigError(f"decisiones.md: motivo inválido en «{f['situacion']}» (solo admite {{pais}} y {{original}})") from None
        ingreso[f["situacion"]] = ReglaIngreso(f["accion"], f["motivo"])
    faltan = [s for s in SITUACIONES_INGRESO if s not in ingreso]
    if faltan:
        raise ConfigError(f"decisiones.md: faltan reglas de ingreso para {', '.join(faltan)}")
    return ingreso


def _familias(t) -> Tuple[FamiliaTitulo, ...]:
    filas = _tabla(t, "familias_del_titulo", "prefiltro.md", ("familia", "peso", "raices"))
    familias = []
    for f in filas:
        peso = _entero(f["peso"], f"prefiltro.md: peso de «{f['familia']}»")
        raices = tuple(r.strip() for r in f["raices"].split(",") if r.strip().rstrip("*"))
        if not peso or not raices:
            raise ConfigError(f"prefiltro.md: la familia «{f['familia']}» necesita un peso distinto de 0 y alguna raíz")
        familias.append(FamiliaTitulo(f["familia"], peso, raices))
    if len({f.nombre for f in familias}) != len(familias):
        raise ConfigError("prefiltro.md: hay familias del título repetidas")
    if not any(f.peso > 0 for f in familias):
        raise ConfigError("prefiltro.md: hace falta al menos una familia del título con peso positivo")
    return tuple(familias)


def _prefiltro(carpeta: Path, prioridad_pais: Dict[str, int]) -> ConfigPrefiltro:
    t = _archivo(carpeta, "prefiltro.md")
    r = _reglas(t, "prefiltro.md", ("puntuacion_minima", "prioridad_pais_por_defecto"))
    orden = tuple((f["criterio"], f["sentido"]) for f in _tabla(t, "orden_del_detalle", "prefiltro.md", ("criterio", "sentido")))
    for criterio, sentido in orden:
        if criterio not in CRITERIOS_ORDEN or sentido not in ("asc", "desc"):
            raise ConfigError(f"prefiltro.md: orden inválido «{criterio} {sentido}» (criterios: {', '.join(CRITERIOS_ORDEN)})")
    return ConfigPrefiltro(_entero(r["puntuacion_minima"], "prefiltro.md: puntuacion_minima"), _familias(t),
                           prioridad_pais, _entero(r["prioridad_pais_por_defecto"], "prefiltro.md: prioridad_pais_por_defecto"), orden)


def _cv(carpeta: Path) -> ConfigCv:
    t = _archivo(carpeta, "cv.md")
    cvs = tuple(CvBase(f["id"], f["archivo"], f["perfil"]) for f in _tabla(t, "cv_base", "cv.md", ("id", "archivo", "perfil")))
    if len({c.id for c in cvs}) != len(cvs):
        raise ConfigError("cv.md: hay ids de CV repetidos")
    r = _reglas(t, "cv.md", ("umbral_afinidad", "tope_rutina"))
    umbral = _entero(r["umbral_afinidad"], "cv.md: umbral_afinidad")
    if not 0 <= umbral <= 100:
        raise ConfigError("cv.md: umbral_afinidad debe estar entre 0 y 100")
    return ConfigCv(cvs, umbral, _entero(r["tope_rutina"], "cv.md: tope_rutina"))


def cargar_cv(carpeta) -> ConfigCv:
    """Solo inputs/cv.md: lo usa la entrevista antes de que exista el resto de inputs/."""
    return _cv(Path(carpeta))


def cargar_prefiltro(carpeta) -> ConfigPrefiltro:
    """Solo inputs/prefiltro.md (sin prioridades de país): para probar las familias del título durante la entrevista."""
    return _prefiltro(Path(carpeta), {})


def _validar_regex(config: Config) -> None:
    """Una expresión «re:» mal escrita falla al arrancar, no después de gastar una petición."""
    i = config.idioma
    expresiones = list(i.pasa) + list(i.rechaza) + list(i.negaciones) + [t.termino for t in config.terminos]
    for e in expresiones:
        try:
            patron(e)
        except re.error as err:
            raise ConfigError(f"expresión regular inválida «{e}»: {err}") from None


def cargar_config(carpeta_inputs) -> Config:
    carpeta = Path(carpeta_inputs)
    ubicaciones, aceptados, excluidos, prioridad_pais = _ubicaciones(carpeta)
    lotes, cadencias, escalada = _lotes(carpeta)
    config = Config(ubicaciones, aceptados, _terminos(carpeta), _modalidad(carpeta), _idioma(carpeta), lotes,
                    _prefiltro(carpeta, prioridad_pais), _decisiones(carpeta), escalada, _cv(carpeta), cadencias, excluidos)
    for t in config.terminos:
        config.cadencia(t.prioridad)   # falla pronto si falta una cadencia
    _validar_regex(config)
    textos.cargar(carpeta)   # falla pronto si inputs/mensajes/ está mal
    return config
