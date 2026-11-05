"""Comando `geoids`: resuelve con LinkedIn el geo_id de las ubicaciones de inputs/ubicaciones.md y, con --escribir,
lo guarda en el archivo. Sin geo_id la lista de empleos aplica la ubicación de la cuenta y la búsqueda se pierde.
Una búsqueda por ubicación, al ritmo de las consultas y con el bloqueo."""
from __future__ import annotations

from pathlib import Path

from collector.comandos.ejecucion import _avisador, _con_bloqueo, _ritmo
from collector.config.cargar import cargar_config
from collector.config.ubicaciones_md import fijar_geo_id
from collector.linkedin import geoids, lectura
from collector.linkedin.sesion_runner import LinkedinSesion
from collector.util import reloj


def _elegidas(cfg, args) -> list:
    if args.frases:
        return list(args.frases)
    return [u.frase for u in cfg.ubicaciones if args.todas or not u.geo_id]


def geoids_cmd(args) -> int:
    cfg = cargar_config(args.inputs)
    frases = _elegidas(cfg, args)
    if not frases:
        print("Todas las ubicaciones de ubicaciones.md tienen geo_id. Usa --todas para comprobarlas otra vez.")
        return 0
    print(f"Ubicaciones a resolver ({len(frases)}): {', '.join(frases)}", flush=True)
    if args.dry_run:
        print("[simulacro] no se ha hecho ninguna petición.")
        return 0
    return _con_bloqueo(args, cfg, lambda: _resolver_todas(args, cfg, frases))


def _resolver_todas(args, cfg, frases) -> int:
    ritmo = _ritmo(cfg, "consultas", cfg.lotes.entero("consultas_por_lote"))
    resultados = []
    with LinkedinSesion(args.raiz, cfg, _avisador(args)) as cli:
        termino = cfg.terminos[0].termino if cfg.terminos else "analyst"
        cli._ir(lectura.url_busqueda(termino, "", cfg.modalidad.filtro, 30))
        for frase in frases:
            ritmo.esperar()
            r = geoids.resolver(cli._page, frase)
            cli._vigilar()
            resultados.append(r)
            _mostrar(r, cfg)
    return _guardar(args, resultados)


def _mostrar(r: dict, cfg) -> None:
    estado = "OK" if geoids.fiable(r) else "REVISAR"
    lugar = r["desplegable"] or "(sin sugerencias)"
    print(f"{estado:8} {r['frase']:22} geo_id={r['geo_id'] or '-':>11}  LinkedIn: {lugar}", flush=True)
    leidas = [lectura.tarjeta("0", t, cfg.modalidad.etiquetas, reloj.ahora()) for t in r["tarjetas"]]
    muestra = [t["location"] for t in leidas if t and t["location"]][:5]
    if muestra:
        print(f"         ubicación de las tarjetas: {' · '.join(muestra)}", flush=True)


def _guardar(args, resultados) -> int:
    revisar = [r["frase"] for r in resultados if not geoids.fiable(r)]
    if args.escribir:
        ruta = Path(args.inputs) / "ubicaciones.md"
        texto = ruta.read_text(encoding="utf-8")
        for r in resultados:
            if geoids.fiable(r):
                texto = fijar_geo_id(texto, r["frase"], r["geo_id"])
        ruta.write_text(texto, encoding="utf-8")
        print(f"Guardados en {ruta}: {len(resultados) - len(revisar)} geo_id.")
    if revisar:
        print(f"Para revisar a mano (no se guardan): {', '.join(revisar)}. Prueba otra frase o quítala de ubicaciones.md.")
    return 0 if not revisar else 1
