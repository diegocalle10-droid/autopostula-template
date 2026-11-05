"""Lo que rodea a run-continuo: preguntar las horas, subir a Neon al arrancar y al terminar, y avisar por Telegram
del resumen y de cualquier parada anómala (429, parada total, disyuntor, error, Ctrl+C, subida fallida)."""
from __future__ import annotations

import sys
from datetime import datetime
from typing import Callable, List, Optional

from collector.db import eventos_repo
from collector.online import conexion, consultas, mensajes, notificador, subir
from collector.pipeline import breaker
from collector.util import apagado, reloj

FINALES_NORMALES = ("tiempo cumplido", "agenda agotada y sin detalles pendientes", "no hay combinaciones pendientes")



def preguntar_horas(horas: float, defecto: float, entrada: Callable[[str], str] = input,
                    interactivo: Optional[bool] = None) -> float:
    """Sin --horas y con terminal, pregunta cuánto debe correr. Vacío, o sin terminal, = `defecto` (horas_por_defecto)."""
    if horas > 0:
        return horas
    if not (sys.stdin.isatty() if interactivo is None else interactivo):
        return defecto
    while True:
        try:
            r = entrada(f"¿Cuántas horas debe correr? (vacío = {defecto:g}): ").strip().replace(",", ".")
            valor = float(r) if r else defecto
            if valor > 0:
                return valor
        except ValueError:
            pass
        print("Escribe un número mayor que 0, por ejemplo 2 o 1.5.")


class Subida(str):
    """Cómo fue la subida a Neon, en una frase para el resumen; `fallida` dice si hay que alertar."""
    fallida = False


def subir_si_hay(args, con, cuando: str) -> Subida:
    """Sube la cola local."""
    if not subir.total_pendientes(con):
        return Subida(mensajes.linea("subida_sin_cambios"))
    abrir = conexion.abridor(args.raiz)
    if not abrir:
        print(f"{cuando}: hay datos por subir, pero falta {conexion.VARIABLE}; se quedan en la cola local.", flush=True)
        return Subida(mensajes.linea("subida_no_configurada", variable=conexion.VARIABLE))
    print(f"{cuando}: subiendo a Neon...", flush=True)
    if subir.con_reintentos(con, abrir, log=lambda m: print(m, flush=True)):
        return Subida(mensajes.linea("subida_completa"))
    fallo = Subida(mensajes.linea("subida_fallida", n=sum(subir.total_pendientes(con).values())))
    fallo.fallida = True
    return fallo


def anomalia(con, r, ahora_iso: str) -> Optional[tuple]:
    """(título, datos) si la captura se paró por algo distinto de un final normal; None si terminó bien."""
    if r.motivo is None or r.motivo in FINALES_NORMALES:
        return None
    pausa = eventos_repo.pausa_activa(con, ahora_iso)
    sospecha = eventos_repo.pausa_activa_con(con, ahora_iso, breaker.MARCA_SOSPECHA)
    if eventos_repo.pausa_activa_con(con, ahora_iso, "[parada_total]"):
        titulo = mensajes.linea("alerta_titulo_parada_total")
    elif sospecha:
        titulo = mensajes.linea("alerta_titulo_sospecha")
    elif r.limite:
        titulo = mensajes.linea("alerta_titulo_limite")
    else:
        titulo = mensajes.linea("alerta_titulo_detenida")
    datos = [mensajes.linea("alerta_motivo", motivo=r.motivo)]
    if sospecha:
        datos.append(mensajes.linea("alerta_sospecha"))
    elif pausa and pausa["pausa_hasta"] != breaker.SIN_PLAZO:
        datos.append(mensajes.linea("alerta_pausa", hasta=mensajes.hora(reloj.de_iso(pausa["pausa_hasta"]))))
    return titulo, datos


def _enviar(args, texto: str) -> None:
    notif = notificador.cargar(args.raiz)
    if not notif:
        return
    try:
        notif.texto(texto)
    except Exception as e:   # sin Telegram la captura no se detiene; queda en la consola
        print(f"Aviso por Telegram fallido: {e}", flush=True)


def alertar(args, titulo: str, datos: List[str]) -> None:
    _enviar(args, mensajes.alerta_captura(titulo, mensajes.hora(reloj.ahora()), datos))


def _alerta_subida(args, subida: Subida) -> None:
    if subida.fallida:
        alertar(args, mensajes.linea("alerta_titulo_subida"),
                [mensajes.linea("alerta_subida", subida=subida), mensajes.linea("alerta_reintento")])


def avisar_fin(args, con, r, subida: Subida, apagado_a: Optional[datetime] = None) -> None:
    ahora = reloj.ahora()
    problema = anomalia(con, r, reloj.a_iso(ahora))
    if problema:
        alertar(args, *problema)
    _alerta_subida(args, subida)
    cierre = mensajes.fin_captura(mensajes.hora_corta(apagado_a) if apagado_a else None)
    _enviar(args, mensajes.captura(mensajes.fecha(ahora), r.motivo or "-", r, subida, consultas.ofertas_por_revisar(conexion.abridor(args.raiz)), cierre))


def cerrar_detalles(args, con, r) -> None:
    """Fin de `detail`: sube lo pendiente y avisa por Telegram, con alerta si se paró por algo anómalo."""
    ahora = reloj.ahora()
    subida = subir_si_hay(args, con, "Al terminar")
    if r.detenida_por:
        alertar(args, mensajes.linea("alerta_titulo_tanda"), [mensajes.linea("alerta_motivo", motivo=r.detenida_por)])
    _alerta_subida(args, subida)
    _enviar(args, mensajes.tanda_detalles(mensajes.fecha(ahora), r, subida, consultas.ofertas_por_revisar(conexion.abridor(args.raiz))))


def ejecutar(args, con, flujo, minutos_apagado: int = 0):
    """Sube lo pendiente, corre el flujo y, pase lo que pase, sube al final y avisa. Salvo con Ctrl+C, programa el
    apagado del PC `minutos_apagado` minutos después (0 = no apagar) y lo dice en el aviso."""
    subir_si_hay(args, con, "Al arrancar")
    try:
        r = flujo.ejecutar()
    except KeyboardInterrupt:
        alertar(args, mensajes.linea("alerta_titulo_ctrl_c"),
                [mensajes.linea("alerta_subida", subida=subir_si_hay(args, con, "Al terminar"))])
        raise
    except Exception as e:
        apagar = apagado.programar(minutos_apagado, reloj.ahora())
        alertar(args, mensajes.linea("alerta_titulo_error", tipo=type(e).__name__),
                [str(e)[:300], mensajes.linea("alerta_subida", subida=subir_si_hay(args, con, "Al terminar"))]
                + ([mensajes.fin_captura_apagado(mensajes.hora_corta(apagar))] if apagar else []))
        raise
    apagar = apagado.programar(minutos_apagado, reloj.ahora())
    avisar_fin(args, con, r, subir_si_hay(args, con, "Al terminar"), apagar)
    return r
