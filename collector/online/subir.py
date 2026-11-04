"""Subida de la SQLite local a Neon. La cola `sync_pendientes` guarda qué falta; una clave sale de la cola
solo después de que Neon confirme (commit), así que un corte se retoma donde quedó y repetir no duplica."""
from __future__ import annotations

import sqlite3
import time
from typing import Callable, Dict, List, Tuple

# Orden por claves foráneas. Clave primaria de cada tabla = (k1[, k2]) de la cola.
ORDEN = ["ofertas", "combinaciones", "consultas", "oferta_keywords", "hallazgos", "eventos"]
PK: Dict[str, Tuple[str, ...]] = {
    "ofertas": ("job_id",), "oferta_keywords": ("job_id", "keyword"), "combinaciones": ("combinacion_id",),
    "consultas": ("consulta_id",), "hallazgos": ("job_id", "consulta_id"), "eventos": ("evento_id",),
}
LOTE = {"ofertas": 100}
LOTE_POR_DEFECTO = 500
Clave = Tuple[str, ...]


def _tipado(tabla: str, clave: Clave) -> list:
    """Las claves enteras se guardan como texto en la cola; vuelven a entero."""
    return [int(v) if c.endswith("_id") and c != "job_id" else v for c, v in zip(PK[tabla], clave)]


def columnas(con: sqlite3.Connection, tabla: str) -> List[str]:
    return [f["name"] for f in con.execute(f"PRAGMA table_info({tabla})")]


def pendientes(con: sqlite3.Connection, tabla: str, limite: int) -> List[Clave]:
    n = len(PK[tabla])
    orden = "(o.duplicada_de IS NOT NULL), p.k1" if tabla == "ofertas" else "p.k1, p.k2"
    union = "LEFT JOIN ofertas o ON o.job_id = p.k1" if tabla == "ofertas" else ""
    filas = con.execute(f"SELECT p.k1, p.k2 FROM sync_pendientes p {union} WHERE p.tabla = ? ORDER BY {orden} LIMIT ?",
                        (tabla, limite)).fetchall()
    return [tuple(f[:n]) for f in filas]


def _filas_locales(con: sqlite3.Connection, tabla: str, claves: List[Clave]) -> Dict[Clave, tuple]:
    cols, pk = columnas(con, tabla), PK[tabla]
    cond = " OR ".join("(" + " AND ".join(f"{c} = ?" for c in pk) + ")" for _ in claves)
    params = [v for k in claves for v in _tipado(tabla, k)]
    filas = con.execute(f"SELECT {', '.join(cols)} FROM {tabla} WHERE {cond}", params).fetchall()
    idx = [cols.index(c) for c in pk]
    return {tuple(str(f[i]) for i in idx): tuple(f) for f in filas}


def _upsert(cur, tabla: str, cols: List[str], filas: List[tuple]) -> None:
    pk = PK[tabla]
    huecos = "(" + ", ".join(["%s"] * len(cols)) + ")"
    cambios = [c for c in cols if c not in pk]
    accion = ("DO UPDATE SET " + ", ".join(f"{c} = EXCLUDED.{c}" for c in cambios)) if cambios else "DO NOTHING"
    if tabla == "ofertas":
        accion += " WHERE ofertas.revisada_en IS NULL"   # lo que el usuario revisó en Neon manda
    sql = (f"INSERT INTO {tabla} ({', '.join(cols)}) VALUES {', '.join([huecos] * len(filas))} "
           f"ON CONFLICT ({', '.join(pk)}) {accion}")
    cur.execute(sql, [v for f in filas for v in f])


def _borrar(cur, tabla: str, claves: List[Clave]) -> None:
    cond = " AND ".join(f"{c} = %s" for c in PK[tabla])
    for k in claves:
        cur.execute(f"DELETE FROM {tabla} WHERE {cond}", _tipado(tabla, k))


def _subir_lote(con, pg, tabla: str, claves: List[Clave]) -> int:
    locales = _filas_locales(con, tabla, claves)
    cur = pg.cursor()
    if locales:
        _upsert(cur, tabla, columnas(con, tabla), list(locales.values()))
    _borrar(cur, tabla, [k for k in claves if tuple(str(v) for v in k) not in locales])
    pg.commit()   # solo ahora la cola puede olvidar estas claves
    for k in claves:
        con.execute("DELETE FROM sync_pendientes WHERE tabla = ? AND k1 = ? AND k2 = ?",
                    (tabla, k[0], k[1] if len(k) > 1 else ""))
    con.commit()
    return len(claves)


def subir_pendientes(con: sqlite3.Connection, pg, log: Callable[[str], None] = print) -> Dict[str, int]:
    """Vacía la cola por lotes y por tabla. Si algo falla, lo ya confirmado queda subido y el resto sigue en cola."""
    hechas: Dict[str, int] = {}
    for tabla in ORDEN:
        while True:
            claves = pendientes(con, tabla, LOTE.get(tabla, LOTE_POR_DEFECTO))
            if not claves:
                break
            hechas[tabla] = hechas.get(tabla, 0) + _subir_lote(con, pg, tabla, claves)
        if hechas.get(tabla):
            log(f"  {tabla}: {hechas[tabla]} filas subidas")
    return hechas


def con_reintentos(con, abrir: Callable, log: Callable[[str], None] = print, intentos: int = 3,
                   espera: Callable[[float], None] = time.sleep) -> bool:
    """Hasta `intentos` subidas seguidas, cada una con conexión nueva y retomando la cola. True si quedó todo subido."""
    for n in range(1, intentos + 1):
        try:
            pg = abrir()
            try:
                subir_pendientes(con, pg, log)
            finally:
                pg.close()
            return True
        except Exception as e:   # red, Neon dormido, conexión cortada...
            log(f"  subida a Neon: intento {n}/{intentos} fallido ({type(e).__name__})")
            if n < intentos:
                espera(5 * n)
    log("  La subida falló 3 veces: lo pendiente queda en la cola y se sube al empezar la próxima ejecución.")
    return False


def total_pendientes(con: sqlite3.Connection) -> Dict[str, int]:
    return {f["tabla"]: f["n"] for f in con.execute("SELECT tabla, COUNT(*) AS n FROM sync_pendientes GROUP BY tabla")}
