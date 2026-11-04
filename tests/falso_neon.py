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
