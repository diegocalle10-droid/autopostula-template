"""Protocolo de sesión de LinkedIn: una vez cada día de ejecución se abre el inicio y se comprueba que la sesión vale.
Si no vale, se avisa por Telegram y se espera a que el usuario inicie sesión en la ventana (email y contraseña de LinkedIn).
Aquí también se clasifica lo que LinkedIn devuelve cuando no es lo esperado."""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Callable, Optional


ESPERA_LOGIN_S = 600
TEXTO_CORTO = 1200
MARCADOR = ".sesion_validada"
_SESION = re.compile(r"/login|authwall|/uas/login", re.I)
_VERIFICACION = re.compile(r"checkpoint|captcha|challenge", re.I)
_AVISO_EN_TEXTO = re.compile(r"actividad inusual|unusual activity|no eres un robot|not a robot|cuenta (ha sido )?restringida|"
                             r"account (has been )?restricted|too many requests|demasiadas solicitudes", re.I)


def clasificar(url: str, status: Optional[int], texto: str) -> Optional[str]:
    """None si la página es normal; 'limite' (429, captcha, verificación, restricción) o 'sesion' (pide iniciar sesión).
    El texto solo cuenta en páginas cortas: un aviso de LinkedIn es una pantalla casi vacía, y una oferta de fraude puede
    decir «actividad inusual» en su descripción."""
    aviso_en_texto = len(texto or "") < TEXTO_CORTO and _AVISO_EN_TEXTO.search(texto or "")
    if status in (429, 999) or _VERIFICACION.search(url) or aviso_en_texto:
        return "limite"
    return "sesion" if _SESION.search(url) else None


def dentro(url: str) -> bool:
    return "linkedin.com" in url and clasificar(url, None, "") is None and any(r in url for r in ("/feed", "/jobs", "/mynetwork", "/in/"))


def validada_hoy(perfil: Path, hoy: str) -> bool:
    marca = Path(perfil) / MARCADOR
    return marca.exists() and marca.read_text(encoding="utf-8").strip() == hoy


def marcar(perfil: Path, hoy: str) -> None:
    Path(perfil).mkdir(parents=True, exist_ok=True)
    (Path(perfil) / MARCADOR).write_text(hoy, encoding="utf-8")


def protocolo(page, perfil: Path, hoy: str, avisar: Callable[..., None], espera_s: int = ESPERA_LOGIN_S,
              reloj: Callable[[], float] = time.time) -> bool:
    """True si hay sesión válida. Una vez comprobada, no se repite hasta el día siguiente. `avisar(clave, **datos)` lo pone quien llama; los textos viven en inputs/mensajes/."""
    if validada_hoy(perfil, hoy):
        return True
    page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    if _VERIFICACION.search(page.url):
        avisar("linkedin_verificacion", url=page.url[:100])
        return False
    if not dentro(page.url):
        avisar("linkedin_sesion_caducada")
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=60000)
        print("Inicia sesión en la ventana de Chrome. La espera dura como máximo 10 minutos.", flush=True)
        limite = reloj() + espera_s
        while reloj() < limite and not dentro(page.url):
            page.wait_for_timeout(2000)
        if not dentro(page.url):
            return False
    marcar(perfil, hoy)
    return True
