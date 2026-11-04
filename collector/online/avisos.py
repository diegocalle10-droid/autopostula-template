"""Bandeja de salida de mensajes de texto en Neon (`avisos`). Encolar va en la misma transacción que el cambio que
lo motiva; enviar los saca en orden. Uno que falla queda pendiente para la próxima pasada (o la del cron diario de la Action)."""
from __future__ import annotations

from typing import Callable

EnviarTexto = Callable[[str], None]


def encolar(pg, texto: str, tipo: str = "texto") -> None:
    """Sin commit: lo hace quien encola, junto con su propio cambio."""
    pg.cursor().execute("INSERT INTO avisos (texto, tipo) VALUES (%s, %s)", (texto, tipo))


def enviar_pendientes(pg, enviar: EnviarTexto, ahora: str, log: Callable[[str], None] = print) -> int:
    cur = pg.cursor()
    cur.execute("SELECT aviso_id, texto FROM avisos WHERE enviado_en IS NULL ORDER BY aviso_id")
    enviados = 0
    for aviso_id, texto in cur.fetchall():
        try:
            enviar(texto)
        except Exception as e:
            log(f"AVISO FALLIDO {aviso_id}: {e}")
            break   # se conserva el orden: lo que queda sale en la próxima pasada
        pg.cursor().execute("UPDATE avisos SET enviado_en = %s WHERE aviso_id = %s", (ahora, aviso_id))
        pg.commit()
        enviados += 1
    return enviados
