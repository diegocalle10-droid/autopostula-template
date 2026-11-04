"""Errores de la frontera con LinkedIn. El resto del programa solo conoce estos tipos."""
from __future__ import annotations


class LinkedinError(Exception):
    def __init__(self, codigo: str, mensaje: str):
        super().__init__(f"{codigo}: {mensaje}")
        self.codigo = codigo
        self.mensaje = mensaje


class LimiteError(LinkedinError):
    """429, captcha, verificación o restricción: hay que parar, no reintentar."""


class NoEncontradaError(LinkedinError):
    """La oferta ya no existe."""


class SesionError(LinkedinError):
    """No hay sesión válida (caducó, o no se completó el inicio de sesión)."""
