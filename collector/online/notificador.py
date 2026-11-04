"""Único punto de salida a Telegram: carga el token y el chat una sola vez y envía textos y PDF."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from collector.online import conexion, telegram


class Notificador:
    def __init__(self, token: str, chat: str):
        self._token, self._chat = token, chat

    def texto(self, texto: str) -> None:
        telegram.enviar_mensaje(self._token, self._chat, texto)

    def documento(self, pdf: Path, texto: str) -> None:
        telegram.enviar_documento(self._token, self._chat, pdf, texto)


def cargar(raiz) -> Optional[Notificador]:
    """None si falta el token o el chat."""
    token = conexion.cargar_variable(Path(raiz), "TELEGRAM_BOT_TOKEN")
    chat = conexion.cargar_variable(Path(raiz), "TELEGRAM_CHAT_ID")
    return Notificador(token, chat) if token and chat else None


def avisador(raiz, formato):
    """Función `avisar(clave, **datos)` para quien no debe conocer Telegram (p. ej. el protocolo de sesión de LinkedIn).
    `formato(clave, **datos)` arma el texto. Si Telegram falla o no está configurado, el aviso queda en la consola."""
    notif = cargar(raiz)

    def avisar(clave: str, **datos: object) -> None:
        if not notif:
            print(f"(sin Telegram) {clave} {datos}", flush=True)
            return
        try:
            notif.texto(formato(clave, **datos))
        except RuntimeError as e:
            print(f"No se pudo avisar por Telegram: {e}", flush=True)
    return avisar
