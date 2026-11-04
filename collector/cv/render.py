"""Markdown de un CV -> PDF apto para ATS: una columna, texto negro seleccionable, sin tablas ni imágenes."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

MAX_PAGINAS = 2
TAMANOS = (10.0, 9.5, 9.0, 8.5)      # se prueba de mayor a menor hasta que cabe en MAX_PAGINAS
_NEGRITA = re.compile(r"\*\*(.+?)\*\*")
_SUSTITUTOS = {"→": "->", "≥": ">=", "≤": "<=", "✓": "", "•": "-"}

Bloque = Tuple[str, str]   # (tipo, texto): h1 | h2 | h3 | li | p | cabecera


def _compatible(texto: str) -> str:
    """Las fuentes estándar del PDF solo cubren cp1252: lo demás se sustituye o se descarta."""
    salida = []
    for c in texto:
        try:
            c.encode("cp1252")
            salida.append(c)
        except UnicodeEncodeError:
            salida.append(_SUSTITUTOS.get(c, ""))
    return "".join(salida)


def _inline(texto: str) -> str:
    seguro = _compatible(texto).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return _NEGRITA.sub(r"<b>\1</b>", seguro)


def bloques(markdown: str) -> List[Bloque]:
    """Subconjunto de Markdown que usan los CV: #, ##, ###, listas con «-» y párrafos. Lo anterior al primer ## es la cabecera."""
    salida: List[Bloque] = []
    en_cabecera = True
    for linea in markdown.splitlines():
        t = linea.strip()
        if not t:
            continue
        if t.startswith("### "):
            salida.append(("h3", t[4:]))
        elif t.startswith("## "):
            en_cabecera = False
            salida.append(("h2", t[3:]))
        elif t.startswith("# "):
            salida.append(("h1", t[2:]))
        elif t[:2] in ("- ", "* "):
            salida.append(("li", t[2:]))
        else:
            salida.append(("cabecera" if en_cabecera else "p", t))
    return salida


def _estilos(tam: float) -> dict:
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=tam, leading=tam * 1.28, textColor="black")
    return {
        "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=tam + 6, leading=(tam + 6) * 1.2,
                             alignment=TA_CENTER, spaceAfter=2),
        "cabecera": ParagraphStyle("cab", parent=base, alignment=TA_CENTER, spaceAfter=1),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=tam + 0.5, spaceBefore=tam * 0.9,
                             spaceAfter=2),
        "h3": ParagraphStyle("h3", parent=base, fontName="Helvetica-Bold", spaceBefore=tam * 0.5, spaceAfter=1),
        "p": ParagraphStyle("p", parent=base, spaceAfter=2),
        "li": ParagraphStyle("li", parent=base, leftIndent=12, bulletIndent=2, spaceAfter=1.5),
    }


def _elementos(markdown: str, tam: float) -> list:
    estilos = _estilos(tam)
    salida: list = []
    for tipo, texto in bloques(markdown):
        if tipo == "h2":
            texto = texto.upper()
        salida.append(Paragraph(_inline(texto), estilos[tipo], bulletText="-" if tipo == "li" else None))
    salida.append(Spacer(1, 1))
    return salida


def generar_pdf(markdown: str, ruta: Path, titulo: str = "") -> Tuple[int, float]:
    """Escribe el PDF con la letra más grande con la que cabe en MAX_PAGINAS. Devuelve (páginas, tamaño de letra)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    paginas = tam = 0
    for tam in TAMANOS:
        doc = SimpleDocTemplate(str(ruta), pagesize=A4, title=_compatible(titulo), author="",
                                leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm, bottomMargin=15 * mm)
        doc.build(_elementos(markdown, tam))
        paginas = doc.page
        if paginas <= MAX_PAGINAS:
            break
    return paginas, tam
