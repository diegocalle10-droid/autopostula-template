"""Reglas puras sobre el Markdown de un CV reescrito: marcadores internos, defectos de estilo y nombres de carpeta."""
from __future__ import annotations

import re
from typing import Iterator, List

from collector.util.texto import normalizar

RAYA_LARGA = "—"
SECCIONES_DE_DATOS = ("formacion", "certificacion", "stack", "habilidad", "competencia", "idioma", "estudio", "educacion")
_MARCADOR = re.compile(r"[ \t]*\[inferida\]", re.IGNORECASE)
_NO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")
_NO_ARCHIVO = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_ESPACIOS = re.compile(r"\s+")
_PLANTILLA = re.compile(r"\[[^\]]*\]|\{[^}]*\}|<[^>]+>|(?-i:\bTODO\b|\bXXX+\b)|lorem ipsum", re.IGNORECASE)   # TODO/XXX solo en mayúsculas: «todo» es español


def quitar_marcadores(markdown: str) -> str:
    """Las habilidades inferidas se marcan `[inferida]` para el control interno; el CV final no las lleva."""
    return _MARCADOR.sub("", markdown)


def _prosa(markdown: str) -> Iterator[str]:
    """El texto libre (título, perfil y logros). Quedan fuera los títulos, el contacto, la línea de empresa y fechas de
    cada puesto y las secciones de datos (formación, certificaciones, stack): ahí la raya larga es un separador legítimo."""
    seccion, tras_puesto = "", False
    for linea in markdown.splitlines():
        s = linea.strip()
        if s.startswith("#"):
            seccion, tras_puesto = normalizar(s.lstrip("#")), s.startswith("### ")
        elif not s:
            continue
        elif tras_puesto:
            tras_puesto = False
            if s.startswith("- "):
                yield s
        elif "@" not in s and not seccion.startswith(SECCIONES_DE_DATOS):
            yield s


def problemas(markdown: str) -> List[str]:
    """Defectos que impiden dar por bueno un CV reescrito. Lista vacía = aceptable."""
    encontrados = []
    if not markdown.strip():
        encontrados.append("el archivo está vacío")
    resto = _PLANTILLA.search(quitar_marcadores(markdown))
    if resto:
        encontrados.append(f"contiene un marcador o texto de plantilla sin resolver: «{resto.group(0)}»")
    if any(RAYA_LARGA in linea for linea in _prosa(markdown)):
        encontrados.append(f"el texto contiene la raya larga «{RAYA_LARGA}»: sustitúyela por coma, punto o paréntesis")
    return encontrados


def nombre_pdf(prefijo: str, titulo: str, largo: int = 100) -> str:
    """'CV - Business Analyst (Madrid).pdf': el título de la vacante sin los caracteres que un archivo no admite."""
    limpio = _ESPACIOS.sub(" ", _NO_ARCHIVO.sub(" ", titulo or "")).strip(" .")[:largo].strip(" .")
    return f"{prefijo} {limpio}.pdf" if limpio else f"{prefijo.rstrip(' -')}.pdf"


def slug(texto: str, largo: int = 40) -> str:
    """'Acme S.L. (Madrid)' -> 'acme-s-l-madrid'; apto para nombres de carpeta."""
    return _NO_ALFANUMERICO.sub("-", normalizar(texto)).strip("-")[:largo].strip("-") or "sin-nombre"
