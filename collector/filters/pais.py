"""País de una oferta a partir del texto de ubicación que devuelve LinkedIn."""
from __future__ import annotations

from typing import FrozenSet, Optional, Tuple

from collector.util.texto import encontrar, normalizar

ACEPTADO, EXCLUIDO, DESCONOCIDO = "aceptado", "excluido", "desconocido"


def _buscar(ubicacion: Optional[str], paises: FrozenSet[str]) -> Optional[str]:
    """País de `paises` que es el último tramo de la ubicación o aparece dentro de ella."""
    mapa = {normalizar(p): p for p in paises}
    texto = normalizar(ubicacion or "")
    ultimo = normalizar((ubicacion or "").split(",")[-1])
    if ultimo in mapa:
        return mapa[ultimo]
    for norm, nombre in mapa.items():
        if encontrar(texto, norm):
            return nombre
    return None


def pais_de_oferta(ubicacion: Optional[str], aceptados: FrozenSet[str], excluidos: FrozenSet[str],
                   pais_busqueda: Optional[str]) -> Tuple[Optional[str], str]:
    """(pais, ACEPTADO | EXCLUIDO | DESCONOCIDO). Nunca se descarta por no reconocer un lugar.

    1. País aceptado en la ubicación («Madrid, Community of Madrid, Spain» -> Spain).
    2. País excluido conocido (p. ej. Brasil en una búsqueda regional).
    3. Búsqueda con país esperado (un país, una región o una ciudad de ese país) y ubicación sin nombre de país
       («Santiago Metropolitan Area», «Greater Madrid Metropolitan Area»): ese país.
    4. En cualquier otro caso, DESCONOCIDO: la oferta se evalúa y queda en «revisar».
    """
    aceptado = _buscar(ubicacion, aceptados)
    if aceptado:
        return aceptado, ACEPTADO
    excluido = _buscar(ubicacion, excluidos)
    if excluido:
        return excluido, EXCLUIDO
    if pais_busqueda:
        return pais_busqueda, ACEPTADO
    return None, DESCONOCIDO
