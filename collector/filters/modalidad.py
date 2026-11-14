"""Modalidad de una oferta que LinkedIn no rotula: se deduce de las frases de `modalidades.md` (columna `senales`)."""
from __future__ import annotations

from typing import List, Optional

from collector.config.modelos import ConfigModalidad
from collector.util.texto import normalizar


def modalidad_en_descripcion(descripcion: str, cfg: ConfigModalidad) -> Optional[str]:
    """Nombre de la modalidad que delata la descripción, o None si no hay señal.

    Las frases más largas se buscan primero y se tachan, así «no presencial» no cuenta como «presencial».
    Si hay señales de varias modalidades gana una no aceptada: ante la duda, no es lo que se busca."""
    texto = " " + normalizar(descripcion) + " "
    pares = sorted(((s, m.nombre) for m in cfg.modalidades for s in m.senales), key=lambda p: -len(p[0]))
    hallados: List[str] = []
    for senal, nombre in pares:
        if senal in texto:
            hallados.append(nombre)
            texto = texto.replace(senal, " ")
    return next((n for n in hallados if n not in cfg.aceptadas), hallados[0] if hallados else None)
