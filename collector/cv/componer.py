"""CV a medida = CV/plantilla.md + datos fijos del CV base + lo que redactó la rutina (`contenido`). Funciones puras.

Los datos fijos (nombre, contacto, empresa y fechas de cada puesto, formación, certificaciones, idiomas) salen del CV
base y nunca de la rutina: no se pueden copiar mal. La rutina solo aporta titular, perfil, cargo y viñetas de cada
puesto y el stack."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from collector.util.texto import normalizar

_COMENTARIO = re.compile(r"<!--.*?-->\s*", re.DOTALL)
_PUESTO = re.compile(r"\{\{#puesto\}\}\n?(.*?)\{\{/puesto\}\}\n?", re.DOTALL)
_HUECO = re.compile(r"\{\{(fijo|rutina):(\w+)\}\}")


@dataclass
class Base:
    """Lo fijo de un CV base, con el texto tal como está escrito."""
    nombre: str = ""
    contacto: str = ""
    puestos: List[str] = field(default_factory=list)          # línea de empresa y fechas de cada puesto, en orden
    secciones: Dict[str, List[str]] = field(default_factory=dict)
    idiomas: str = ""


def leer_base(markdown: str) -> Base:
    b, seccion, tras_cargo = Base(), "", False
    for linea in markdown.splitlines():
        s = linea.strip()
        if s.startswith("### "):
            tras_cargo = True
        elif s.startswith("## "):
            seccion, tras_cargo = normalizar(s[3:]), False
            b.secciones.setdefault(seccion, [])
        elif s.startswith("# "):
            b.nombre = s[2:].strip()
        elif not s:
            continue
        elif tras_cargo and not s.startswith("- "):
            b.puestos.append(s)
            tras_cargo = False
        elif not seccion and "@" in s:
            b.contacto = s
        elif seccion and normalizar(s.lstrip("-* ")).startswith("idioma"):
            b.idiomas = s
        elif seccion:
            b.secciones[seccion].append(s)
    return b


def _seccion(b: Base, prefijo: str) -> str:
    return "\n".join(next((ls for k, ls in b.secciones.items() if k.startswith(prefijo)), []))


def _lista(items) -> str:
    return "\n".join(t if t.startswith("- ") else f"- {t}" for t in (str(i).strip() for i in items) if t)


def errores_contenido(contenido, base: Base) -> List[str]:
    """Lo que le falta a `contenido` para poder componer el CV. Lista vacía = se puede."""
    if not isinstance(contenido, dict):
        return ["`contenido` no es un objeto JSON"]
    fallos = [f"`contenido.{k}` vacío o ausente" for k in ("titular", "perfil")
              if not isinstance(contenido.get(k), str) or not contenido[k].strip()]
    puestos, stack = contenido.get("puestos"), contenido.get("stack")
    if not isinstance(puestos, list) or len(puestos) != len(base.puestos):
        fallos.append(f"`contenido.puestos` debe traer {len(base.puestos)} puestos, en el orden del CV base")
    else:
        for i, p in enumerate(puestos, 1):
            if not isinstance(p, dict) or not str(p.get("cargo") or "").strip() or not p.get("vinetas"):
                fallos.append(f"`contenido.puestos[{i}]` necesita `cargo` y `vinetas`")
    if not isinstance(stack, list) or not stack:
        fallos.append("`contenido.stack` vacío o ausente")
    return fallos


def _fijos(b: Base) -> Dict[str, str]:
    return {"nombre": b.nombre, "contacto": b.contacto, "formacion": _seccion(b, "formacion"),
            "certificaciones": _seccion(b, "certificacion"), "idiomas": b.idiomas}


def _rellenar(plantilla: str, fijos: Dict[str, str], rutina: Dict[str, str]) -> str:
    return _HUECO.sub(lambda m: (fijos if m.group(1) == "fijo" else rutina).get(m.group(2), ""), plantilla)


def componer(plantilla: str, base_md: str, contenido) -> Tuple[str, List[str]]:
    """(cv_md, errores). Con errores, cv_md es ''."""
    base = leer_base(base_md)
    errores = errores_contenido(contenido, base)
    if errores:
        return "", errores
    plantilla = _COMENTARIO.sub("", plantilla)
    bloque = _PUESTO.search(plantilla)
    puestos = "\n".join(_rellenar(bloque.group(1), {"empresa_fechas": linea},
                                  {"cargo": str(p["cargo"]).strip(), "vinetas": _lista(p["vinetas"])})
                        for linea, p in zip(base.puestos, contenido["puestos"]))
    cuerpo = plantilla[:bloque.start()] + puestos + "\n" + plantilla[bloque.end():]
    rutina = {"titular": contenido["titular"].strip(), "perfil": contenido["perfil"].strip(),
              "stack": _lista(contenido["stack"])}
    return re.sub(r"\n{3,}", "\n\n", _rellenar(cuerpo, _fijos(base), rutina)).strip() + "\n", []
