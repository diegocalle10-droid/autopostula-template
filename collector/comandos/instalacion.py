"""Puesta en marcha de una instalación nueva: instalar (todo de una vez), doctor, validar-cv, probar-titulos y
telegram-chat-id."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from collector.comandos import datos, online
from collector.config.cargar import cargar_config, cargar_cv, cargar_prefiltro
from collector.config.modelos import ConfigError
from collector.filters.cv_datos import faltas_de_ficha, ficha
from collector.filters.titulo import FiltroTitulos
from collector.online import conexion, mensajes

PENDIENTE = "PENDIENTE"


def instalar(args) -> int:
    """Crea la base local, el esquema de Neon y la agenda, y termina con `doctor`. Se puede repetir sin riesgo."""
    try:
        cargar_config(args.inputs)
    except ConfigError as e:
        print(f"La configuración no está completa: {e}\nHaz primero la entrevista: abre el repositorio en Claude Code "
              "y escribe «configura mi Autopostula» (ver CONFIGURAR.md).")
        return 3
    pasos = (("Base local", datos.init_db), ("Agenda de búsquedas", datos.plan), ("Esquema en Neon", online.online_init))
    for nombre, paso in pasos:
        print(f"\n== {nombre} ==", flush=True)
        if paso(args):
            print(f"Se detuvo en «{nombre}». Corrige lo que indica y vuelve a ejecutar «python cli.py instalar».")
            return 1
    print("\n== Comprobación final ==")
    return doctor(args)


def validar_cv(args) -> int:
    """Muestra lo que se reconoce de cada CV base de inputs/cv.md y falla si falta algo imprescindible.
    Solo lee inputs/cv.md: funciona en el primer paso de la entrevista, con el resto de inputs/ aún vacío."""
    fallos = 0
    for base in cargar_cv(args.inputs).cvs:
        ruta = Path(args.raiz) / base.archivo
        if not ruta.is_file():
            print(f"FALLA {base.id}: no existe {base.archivo}")
            fallos += 1
            continue
        d = ficha(ruta.read_text(encoding="utf-8"))
        faltas = faltas_de_ficha(d)
        print(f"{'FALLA' if faltas else 'OK  '} {base.id} ({base.archivo}): {d['nombre'] or '?'} · {', '.join(d['correo']) or 'sin correo'}"
              f" · {d['puestos']} puestos · {d['estudios']} estudios · {d['certificaciones']} certificaciones"
              f" · idiomas: {', '.join(d['idiomas']) or 'ninguno'}")
        for f in faltas:
            print(f"      - {f}")
        fallos += bool(faltas)
    return 1 if fallos else 0


def telegram_chat_id(args) -> int:
    """Lista los chats que han escrito al bot (getUpdates): el id es el valor de TELEGRAM_CHAT_ID."""
    token = conexion.cargar_variable(Path(args.raiz), "TELEGRAM_BOT_TOKEN")
    if not token:
        print("Falta TELEGRAM_BOT_TOKEN en .env: créalo con @BotFather y vuelve a ejecutar.")
        return 1
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20) as r:
            respuesta = json.load(r)
    except OSError as e:
        print(f"Telegram no responde o el token no es válido ({type(e).__name__}).")
        return 1
    chats = {}
    for u in respuesta.get("result", []):
        chat = (u.get("message") or u.get("channel_post") or {}).get("chat") or {}
        if "id" in chat:
            chats[chat["id"]] = chat.get("first_name") or chat.get("title") or ""
    if not chats:
        print("Aún no hay mensajes: escribe cualquier cosa a tu bot en Telegram y vuelve a ejecutar este comando.")
        return 1
    for chat_id, nombre in chats.items():
        print(f"TELEGRAM_CHAT_ID={chat_id}   ({nombre})")
    return 0


def pendientes_de_configurar() -> list:
    """Ajustes de inputs/mensajes/enlaces.md que siguen sin rellenar."""
    return [c for c in ("repo_github", "neon_project_id", "url_consola_neon", "url_rutina", "hora_rutina")
            if mensajes.ajuste(c).strip().upper() == PENDIENTE]


def doctor(args) -> int:
    """Entorno (datos.doctor) más lo propio de una instalación: secretos, enlaces por rellenar y CV base."""
    fallos = datos.doctor(args)
    for variable in (conexion.VARIABLE, "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        ok = bool(conexion.cargar_variable(Path(args.raiz), variable))
        print(("OK   " if ok else "FALLA ") + f"{variable} en .env" + ("" if ok else " (ver la guía de secretos del README)"))
        fallos += 0 if ok else 1
    pendientes = pendientes_de_configurar()
    if pendientes:
        print(f"AVISO inputs/mensajes/enlaces.md sin rellenar: {', '.join(pendientes)}")
    try:
        fallos += validar_cv(args)
    except ConfigError:
        pass   # ya lo ha dicho la comprobación de inputs/
    return 1 if fallos else 0


def probar_titulos(args) -> int:
    """Puntúa títulos de ejemplo con las familias de inputs/prefiltro.md: cuáles pedirían su detalle y cuáles no."""
    cfg = cargar_prefiltro(args.inputs)
    filtro = FiltroTitulos(cfg)
    for titulo in args.titulos:
        e = filtro.evaluar(titulo)
        estado = "PASA " if e.puntos >= cfg.puntuacion_minima else "FUERA"
        print(f"{estado} {e.puntos:+d}  {titulo}  ({', '.join(e.familias) or 'ninguna familia'})")
    return 0
