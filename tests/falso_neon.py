"""Un 'Neon' de pruebas hecho con otra SQLite: traduce %s a ? y puede cortarse a la N-ésima sentencia."""


class FalsoNeon:
    """Un 'Neon' hecho con otra SQLite: traduce %s a ? y puede cortarse a la N-ésima sentencia."""
    def __init__(self, destino, falla_en=None):
        self.destino, self.falla_en, self.n, self.cerrada = destino, falla_en, 0, False

    def cursor(self):
        return self

    def execute(self, sql, params=()):
        self.n += 1
        if self.falla_en and self.n >= self.falla_en:
            raise ConnectionError("corte")
        self.ultimo = self.destino.execute(sql.replace("%s", "?"), params)

    def fetchall(self):
        return self.ultimo.fetchall()

    def fetchone(self):
        return self.ultimo.fetchone()

    def commit(self):
        self.destino.commit()

    def close(self):
        self.cerrada = True


def esquema_neon_sqlite() -> str:
    """001_neon.sql con lo que 005_cv_keywords.sql añade a `emparejamientos`, en SQLite (que no admite DROP CONSTRAINT)."""
    from collector.online.esquema import CARPETA
    sql = (CARPETA / "001_neon.sql").read_text(encoding="utf-8")
    for viejo, nuevo in (("emparejado_en TEXT NOT NULL, validado_en TEXT, notificado_en TEXT,",
                          "emparejado_en TEXT NOT NULL, validado_en TEXT, notificado_en TEXT, keywords TEXT, contenido TEXT,"),
                         ("AND cv_md IS NOT NULL))", "AND (cv_md IS NOT NULL OR contenido IS NOT NULL)))")):
        assert viejo in sql, viejo
        sql = sql.replace(viejo, nuevo)
    return sql
