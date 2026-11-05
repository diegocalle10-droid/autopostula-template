"""Lectura del texto de las páginas de LinkedIn con sesión: tarjetas de la lista y cabecera de la oferta. Funciones puras."""
from __future__ import annotations

import re
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Optional

from collector.util.texto import normalizar

POR_PAGINA = 25
PREFIJO_ID = "job-card-component-ref-"
TARJETA = f'[componentkey^="{PREFIJO_ID}"][role="button"]'   # lista nueva (2026-11): el id va en `componentkey`
PAGINACION = '[data-testid="pagination-controls-list"]'
ID_JS = f"e => e.getAttribute('componentkey').slice({len(PREFIJO_ID)})"
# Cuando quedan pocas o ninguna oferta que cumpla los filtros, LinkedIn pone un aviso («más resultados relacionados…»,
# «no se han podido encontrar coincidencias exactas…») y debajo ofertas que los ignoran
# (otras modalidades, sin solicitud sencilla): [id, texto, va_tras_el_aviso] por tarjeta.
TARJETAS_JS = r"""s => {
  const aviso = [...document.querySelectorAll('p, span, h2, h3')].find(e => e.children.length === 0 &&
      /(coincidencias exactas|exact match|m[aá]s resultados relacionados|more results related)/i.test(e.textContent || ''));
  return [...document.querySelectorAll(s)].map(e => [(%s)(e), e.innerText,
      !!(aviso && (aviso.compareDocumentPosition(e) & Node.DOCUMENT_POSITION_FOLLOWING))]);
}""" % ID_JS
DESCRIPCION_JS = """() => {
  const h = [...document.querySelectorAll('h2')].find(e => /^(Acerca del empleo|About the job)$/.test((e.textContent || '').trim()));
  if (!h) return '';
  const caja = h.parentElement && h.parentElement.parentElement;
  return caja ? caja.innerText.replace(/^\\s*(Acerca del empleo|About the job)\\s*/, '').trim() : '';
}"""
_SELECCIONADA = re.compile(r"^(seleccionado|selected),\s*", re.I)   # la tarjeta abierta lleva este prefijo para lectores de pantalla
_VERIFICADO = r"(\s*\((empleo verificado|verified job)\)|\s+with verification|\s+verificado)?"
_ETIQUETA = re.compile(r"\(([^()]+)\)\s*$")
_RELATIVA = re.compile(r"\bhace (\d+) (minuto|hora|dia|semana|mes|ano)s?\b|\b(\d+) (minute|hour|day|week|month|year)s? ago\b")
_UNIDAD = {"minuto": "minutes", "minute": "minutes", "hora": "hours", "hour": "hours", "dia": "days", "day": "days",
           "semana": "weeks", "week": "weeks", "mes": "months", "month": "months", "ano": "years", "year": "years"}
_DIAS = {"months": 30, "years": 365}
_TIPO = {"jornada completa": "Full-time", "full-time": "Full-time", "media jornada": "Part-time", "part-time": "Part-time",
         "contrato": "Contract", "contract": "Contract", "temporal": "Temporary", "practicas": "Internship", "internship": "Internship"}
CERRADA = re.compile(r"ya no se aceptan solicitudes|no longer accepting applications", re.I)
NO_DISPONIBLE = re.compile(r"ya no esta disponible|no se (ha )?encontr|no longer available|page not found|no encontramos", re.I)


def url_busqueda(termino: str, ubicacion: str, filtro: str, dias: int, geo_id: Optional[str] = None) -> str:
    """Solo solicitud sencilla (`f_AL=true`): es una regla fija del sistema, no un parámetro.
    La lista nueva ignora el texto de `location` y aplica la ubicación de la cuenta si no recibe `geoId`."""
    q = {"keywords": termino, "location": ubicacion, "f_WT": filtro, "f_TPR": f"r{dias * 86400}", "f_AL": "true"}
    if geo_id:
        q["geoId"] = geo_id
    return "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(q)


def fecha_relativa(texto: str, ahora: datetime) -> Optional[str]:
    """«hace 3 días», «Hace 14 horas», «2 weeks ago» → fecha (AAAA-MM-DD); None si el texto no trae ninguna."""
    m = _RELATIVA.search(normalizar(texto))
    if not m:
        return None
    n, unidad = (int(m.group(1)), m.group(2)) if m.group(1) else (int(m.group(3)), m.group(4))
    medida = _UNIDAD[unidad]
    delta = timedelta(days=n * _DIAS[medida]) if medida in _DIAS else timedelta(**{medida: n})
    return (ahora - delta).date().isoformat()


def _modalidad(linea: str, etiquetas: Dict[str, str]) -> Optional[str]:
    return etiquetas.get(normalizar(linea))


def tarjeta(job_id: str, texto: str, etiquetas: Dict[str, str], ahora: datetime) -> Optional[dict]:
    """Oferta a partir del texto de su tarjeta; None si aún no se ha pintado."""
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    if not lineas:
        return None
    titulo = re.sub(_VERIFICADO + "$", "", _SELECCIONADA.sub("", lineas[0]), flags=re.I).strip()
    repetido = re.compile(re.escape(titulo) + _VERIFICADO, re.I)
    resto = [l for l in lineas[1:] if not repetido.fullmatch(l)]   # LinkedIn repite el título, a veces marcado como verificado
    ubicacion = resto[1] if len(resto) > 1 else ""
    m = _ETIQUETA.search(ubicacion)
    modalidad = _modalidad(m.group(1), etiquetas) if m else None
    if modalidad:
        ubicacion = _ETIQUETA.sub("", ubicacion).strip()
    return {"id": job_id, "title": titulo, "company": resto[0] if resto else "", "location": ubicacion,
            "date": next((f for f in (fecha_relativa(l, ahora) for l in lineas) if f), None), "modalidad": modalidad,
            "url": f"https://www.linkedin.com/jobs/view/{job_id}/"}


def cabecera(texto: str, etiquetas: Dict[str, str]) -> dict:
    """Datos del encabezado de la oferta: lo que va justo antes del botón «Guardar». Vacío si la página no lo trae."""
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    if "Guardar" not in lineas:
        return {}
    fin = lineas.index("Guardar")
    ventana = lineas[max(0, fin - 12):fin]
    donde = next((i for i, l in enumerate(ventana) if "·" in l), None)
    partes = [p.strip() for p in ventana[donde].split("·")] if donde is not None else []
    cola = ventana[(donde or 0):]
    return {"title": ventana[donde - 1] if donde else None, "company": ventana[donde - 2] if donde and donde > 1 else None,
            "location": partes[0] if partes else None, "publicada": partes[1] if len(partes) > 1 else None,
            "modalidad": next((m for m in (_modalidad(l, etiquetas) for l in cola) if m), None),
            "tipo_empleo": next((_TIPO[normalizar(l)] for l in cola if normalizar(l) in _TIPO), None),
            "solicitud_sencilla": any(normalizar(l) in ("solicitud sencilla", "easy apply") for l in cola)}
