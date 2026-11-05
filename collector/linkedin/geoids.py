"""Resuelve el geoId de una ubicación con el desplegable «Ubicación» de la lista de empleos (con sesión) y recoge lo
necesario para validarlo: lo que muestra el desplegable y el texto de las primeras tarjetas."""
from __future__ import annotations

import urllib.parse
from typing import List

from collector.linkedin import lectura
from collector.util.texto import normalizar

DESPLEGABLE = '[aria-label^="Ubicaci"], [aria-label^="Location"]'
CAJA = '[aria-label="Ubicación"], [aria-label="Location"]'
_LEER = """() => ({
  url: location.href,
  desplegable: ((document.querySelector('[aria-label^="Ubicaci"], [aria-label^="Location"]') || {}).ariaLabel || '')
     .replace(/^(Ubicación|Location)\\s*/, ''),
  tarjetas: [...document.querySelectorAll('%s')].slice(0, 8).map(e => e.innerText),
})""" % lectura.TARJETA
_OPCIONES = r"""() => {
  const caja = document.querySelector('[data-geoids="caja"]');
  let panel = caja;
  while (panel && !/^\s*(Ubicaci[oó]n|Location)\s*\n/.test(panel.innerText || '')) panel = panel.parentElement;
  if (!panel) return [];
  const borde = caja.getBoundingClientRect().bottom;
  const hojas = [...panel.querySelectorAll('*')].filter(e => {
    const t = (e.innerText || '').trim();
    if (!t || t.includes('\n') || e.offsetParent === null || e.contains(caja) || e.getBoundingClientRect().top <= borde) return false;
    return !(e.parentElement && (e.parentElement.innerText || '').trim() === t);
  });
  hojas.forEach((e, i) => e.setAttribute('data-geoids-op', String(i)));
  return hojas.map(e => e.innerText.trim()).slice(0, 8);
}"""


def resolver(page, frase: str) -> dict:
    """Escribe `frase` en el desplegable, elige la primera sugerencia y lee el resultado. Sin sugerencias: geo_id None."""
    page.click(DESPLEGABLE)
    caja = page.locator(CAJA).last
    caja.wait_for(timeout=10000)
    caja.evaluate("e => e.setAttribute('data-geoids', 'caja')")
    caja.click()
    caja.press("Control+a")
    caja.press("Backspace")
    caja.type(frase, delay=120)
    page.wait_for_timeout(3500)
    opciones: List[str] = page.evaluate(_OPCIONES)
    if not opciones:
        page.keyboard.press("Escape")
        return {"frase": frase, "geo_id": None, "opciones": [], "desplegable": "", "tarjetas": []}
    page.locator('[data-geoids-op="0"]').click()
    page.wait_for_timeout(15000)
    r = page.evaluate(_LEER)
    geo = urllib.parse.parse_qs(urllib.parse.urlparse(r["url"]).query).get("geoId", [None])[0]
    return {"frase": frase, "geo_id": geo, "opciones": opciones, "desplegable": r["desplegable"], "tarjetas": r["tarjetas"]}


def fiable(r: dict) -> bool:
    """El desplegable muestra la sugerencia elegida y es un lugar entero (sin «, provincia» ni «(80 km)»): un país o región.
    Lo que no lo es («American River, SA (80 km)» al pedir «South America») queda para revisar a mano."""
    lugar = r.get("desplegable") or ""
    return bool(r.get("geo_id") and r.get("opciones") and normalizar(lugar) == normalizar(r["opciones"][0])
                and "," not in lugar and "km)" not in lugar)
