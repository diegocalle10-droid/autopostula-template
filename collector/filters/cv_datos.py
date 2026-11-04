"""Datos que un CV reescrito no puede cambiar respecto a su CV base: nombre, contacto, empresa y fechas de cada puesto,
formación, certificaciones e idiomas con su nivel. No se audita el texto de logros y perfil (es lo que muta) ni las
habilidades del stack: se pueden reordenar, omitir y ampliar con criterio, y la revisión final es humana."""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Set

from collector.util.texto import normalizar

MAX_PROBLEMAS = 10
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(r"(?:https?://|www\.)[^\s·|]+")
_TELEFONO = re.compile(r"[+\d][\d ()+-]{7,}\d")
_MARCA = re.compile(r"\[inferida\]", re.IGNORECASE)
_ETIQUETA = re.compile(r"^\s*[-*]?\s*\*\*[^*]+\*\*\s*")
_SEPARADOR = re.compile(r"\s*[·,]\s*")
GRUPOS = {"estudios": ("formacion", "educacion", "estudio"),
          "certificaciones": ("certificacion", "certificado"),
          "habilidades": ("stack", "habilidad", "competencia", "idioma")}   # las líneas «Idiomas» viven en esa sección


def _n(texto: str) -> str:
    """Texto comparable: sin marcador [inferida], negritas ni acentos, minúsculas y espacios simples."""
    return re.sub(r"\s+", " ", normalizar(_MARCA.sub("", texto).replace("*", ""))).strip()


class _Cv:
    """Lo mínimo del Markdown de un CV: nombre, cabecera, líneas por sección y la línea de empresa y fechas de cada puesto."""

    def __init__(self, markdown: str):
        self.nombre = ""
        self.cabecera: List[str] = []
        self.secciones: Dict[str, List[str]] = {}
        self.puestos: Dict[str, str] = {}
        self._leer(markdown)

    def _leer(self, markdown: str) -> None:
        seccion, puesto = None, None
        for linea in markdown.splitlines():
            s = linea.strip()
            if s.startswith("### "):
                puesto = _n(s[4:])
                self.puestos[puesto] = ""
            elif s.startswith("## "):
                seccion, puesto = _n(s[3:]), None
                self.secciones.setdefault(seccion, [])
            elif s.startswith("# "):
                self.nombre = _n(s[2:])
            elif not s:
                continue
            elif puesto is not None and not self.puestos[puesto] and not s.startswith("- "):
                self.puestos[puesto] = _n(s)
            else:
                (self.cabecera if seccion is None else self.secciones[seccion]).append(s)

    def lineas(self, grupo: str) -> List[str]:
        return [l for clave, ls in self.secciones.items() if clave.startswith(GRUPOS[grupo]) for l in ls]


def _contacto(lineas: Iterable[str]) -> Dict[str, Set[str]]:
    texto = " ".join(lineas)
    return {"correo": {e.lower() for e in _EMAIL.findall(texto)},
            "enlace": {u.lower().rstrip(".,;)/") for u in _URL.findall(texto)},
            "teléfono": {re.sub(r"\D", "", t) for t in _TELEFONO.findall(texto)}}


def _items(lineas: Iterable[str]) -> List[str]:
    return [_n(re.sub(r"^[-*]\s*", "", l)) for l in lineas if l.strip()]


def _idiomas(cv: _Cv) -> List[str]:
    """Cada idioma con su nivel, de las líneas cuya etiqueta es «Idiomas»; separados por «·» o coma."""
    salida = []
    for linea in cv.lineas("habilidades"):
        etiqueta = _ETIQUETA.match(linea)
        if etiqueta and _n(etiqueta.group(0)).startswith("idioma"):
            salida += [h for h in (_n(t).strip(" ()") for t in _SEPARADOR.split(_ETIQUETA.sub("", linea))) if h]
    return salida


def _problemas_contacto(base: _Cv, gen: _Cv) -> List[str]:
    a, b = _contacto(base.cabecera), _contacto(gen.cabecera)
    return [f"{tipo} del contacto {'ausente' if v else 'añadido'}: «{dato}»" for tipo in a
            for v, dato in [(True, d) for d in sorted(a[tipo] - b[tipo])] + [(False, d) for d in sorted(b[tipo] - a[tipo])]]


def _problemas_puestos(base: _Cv, gen: _Cv) -> List[str]:
    """El título del cargo se puede adaptar a la oferta; la línea de empresa y fechas tiene que ser una del CV base."""
    lineas_base = set(base.puestos.values())
    return [f"la empresa o las fechas del puesto «{puesto}» no coinciden con ningún puesto del CV base"
            for puesto, linea in gen.puestos.items() if linea not in lineas_base]


def _problemas_listas(base: _Cv, gen: _Cv) -> List[str]:
    fallos = []
    for grupo in ("estudios", "certificaciones"):
        permitidos = set(_items(base.lineas(grupo)))
        fallos += [f"{grupo}: «{i}» no está en el CV base" for i in _items(gen.lineas(grupo)) if i not in permitidos]
    return fallos


def _problemas_idiomas(base: _Cv, gen: _Cv) -> List[str]:
    texto_base = " ".join(_idiomas(base))
    return [f"idioma «{i}» no está en el CV base" for i in _idiomas(gen) if i not in texto_base]


def verificar_datos(base_md: str, generado_md: str) -> List[str]:
    """Diferencias en los datos que no deben cambiar. Lista vacía = correcto."""
    base, gen = _Cv(base_md), _Cv(generado_md)
    fallos = [] if gen.nombre == base.nombre else [f"el nombre «{gen.nombre}» no coincide con el del CV base"]
    for f in (_problemas_contacto, _problemas_puestos, _problemas_listas, _problemas_idiomas):
        fallos += f(base, gen)
    return fallos[:MAX_PROBLEMAS]


def ficha(markdown: str) -> Dict[str, object]:
    """Lo que la validación reconoce en un CV base y protegerá en cada CV a medida (para `validar-cv`)."""
    cv = _Cv(markdown)
    contacto = _contacto(cv.cabecera)
    return {"nombre": cv.nombre, "correo": sorted(contacto["correo"]), "teléfono": sorted(contacto["teléfono"]),
            "puestos": sum(1 for linea in cv.puestos.values() if linea), "estudios": len(_items(cv.lineas("estudios"))),
            "certificaciones": len(_items(cv.lineas("certificaciones"))), "idiomas": _idiomas(cv)}


def faltas_de_ficha(datos: Dict[str, object]) -> List[str]:
    """Lo imprescindible para que el CV base sirva: nombre, correo, al menos un puesto con su empresa y fechas, y estudios."""
    requisitos = {"nombre": "falta el nombre en la primera línea («# NOMBRE»)",
                  "correo": "falta un correo en la línea de contacto, bajo el nombre",
                  "puestos": "ningún puesto («### Cargo») lleva debajo su línea de empresa y fechas",
                  "estudios": "falta la sección de formación («## FORMACIÓN») con al menos una línea"}
    return [texto for clave, texto in requisitos.items() if not datos[clave]]
