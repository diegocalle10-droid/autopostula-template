"""Envío a Telegram (HTML): textos (sendMessage) y el PDF del CV con su pie (sendDocument, hasta 50 MB)."""
from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

LIMITE_MENSAJE = 4096


def _cuerpo(chat_id: str, pdf: Path, texto: str):
    marca = uuid.uuid4().hex
    campos = b"".join(f'--{marca}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                      for k, v in (("chat_id", chat_id), ("caption", texto), ("parse_mode", "HTML")))
    cabecera = (f'--{marca}\r\nContent-Disposition: form-data; name="document"; filename="{pdf.name}"\r\n'
                "Content-Type: application/pdf\r\n\r\n").encode()
    return campos + cabecera + pdf.read_bytes() + f"\r\n--{marca}--\r\n".encode(), marca


def enviar_documento(token: str, chat_id: str, pdf: Path, texto: str, timeout: float = 60) -> None:
    """Envía el PDF con su pie."""
    cuerpo, marca = _cuerpo(chat_id, pdf, texto)
    _llamar(token, "sendDocument", cuerpo, f"multipart/form-data; boundary={marca}", timeout)


def enviar_mensaje(token: str, chat_id: str, texto: str, timeout: float = 30) -> None:
    """Envía un texto; si pasa del límite de Telegram, se corta."""
    if len(texto) > LIMITE_MENSAJE:
        texto = texto[:LIMITE_MENSAJE - 1] + "…"
    cuerpo = urllib.parse.urlencode({"chat_id": chat_id, "text": texto, "parse_mode": "HTML",
                                     "disable_web_page_preview": "true"}).encode()
    _llamar(token, "sendMessage", cuerpo, "application/x-www-form-urlencoded", timeout)


def _llamar(token: str, metodo: str, cuerpo: bytes, tipo: str, timeout: float) -> None:
    """Cualquier fallo sale como RuntimeError sin la URL (lleva el token)."""
    peticion = urllib.request.Request(f"https://api.telegram.org/bot{token}/{metodo}", data=cuerpo,
                                      headers={"Content-Type": tipo})
    try:
        urllib.request.urlopen(peticion, timeout=timeout).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Telegram respondió {e.code}") from None
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"Telegram no responde ({type(e).__name__})") from None
