"""Huella de una vacante: detecta republicaciones que LinkedIn publica con un id nuevo."""
from __future__ import annotations

import hashlib
from typing import Optional

from collector.util.texto import normalizar


def huella(empresa: Optional[str], titulo: Optional[str], ubicacion: Optional[str]) -> str:
    base = "|".join(normalizar(x or "") for x in (empresa, titulo, ubicacion))
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]
