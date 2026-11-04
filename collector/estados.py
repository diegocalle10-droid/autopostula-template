"""Vocabulario interno del sistema: estados de una oferta. No es configurable (lo fija el esquema)."""
from __future__ import annotations

PENDIENTE = "pendiente"      # aún no se ha pedido su detalle
APTA = "apta"
REVISAR = "revisar"
DESCARTADA = "descartada"

ESTADOS_DE_DECISION = (APTA, REVISAR, DESCARTADA)   # los que puede asignar una regla de inputs/decisiones.md
# Condiciones que puede usar una regla de inputs/decisiones.md. Cada una se evalúa en filters/decision.py; la carga de
# inputs/ solo necesita los nombres, así `config` no depende de `filters`.
CONDICIONES = ("cerrada", "detalle_ilegible", "modalidad_no_aceptada", "nivel_exigente", "nivel_dudoso", "contenido_vigilado_titulo_no",
               "contenido_vigilado_nivel_aceptable", "contenido_vigilado", "pais_desconocido", "siempre")
