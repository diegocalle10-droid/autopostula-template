"""Migraciones numeradas del esquema de Neon (NNN_nombre.sql); la versión vive en `esquema_version`."""
from __future__ import annotations

from pathlib import Path
from typing import List

CARPETA = Path(__file__).parent / "migrations"


def _numero(ruta: Path) -> int:
    return int(ruta.name.split("_", 1)[0])


def version_actual(pg) -> int:
    cur = pg.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS esquema_version (version INTEGER PRIMARY KEY, aplicada_en TEXT NOT NULL)")
    cur.execute("SELECT COALESCE(MAX(version), 0) FROM esquema_version")
    n = cur.fetchone()[0]
    pg.commit()
    return n


def migrar(pg) -> List[int]:
    """Aplica las migraciones que faltan, cada una en su transacción. Devuelve las aplicadas."""
    actual = version_actual(pg)
    aplicadas = []
    for ruta in sorted(CARPETA.glob("*.sql"), key=_numero):
        if _numero(ruta) <= actual:
            continue
        cur = pg.cursor()
        cur.execute(ruta.read_text(encoding="utf-8"))
        cur.execute("INSERT INTO esquema_version (version, aplicada_en) VALUES (%s, to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'))",
                    (_numero(ruta),))
        pg.commit()
        aplicadas.append(_numero(ruta))
    return aplicadas
