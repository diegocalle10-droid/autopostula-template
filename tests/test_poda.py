import unittest

from collector.db import consultas_repo
from collector.db.connection import transaccion
from collector.pipeline import prune
from collector.pipeline.ritmo import Ritmo
from tests.base import Base
from tests.ayudas import obtener_combinacion


class Poda(Base):
    def test_duplica_cadencia_tras_pasadas_sin_nuevas_y_reinicia_contador(self):
        self.con.execute("UPDATE combinaciones SET pasadas_sin_nuevas = 3, ultima_ejecucion = '2026-10-01T00:00:00Z' WHERE combinacion_id = 1")
        with transaccion(self.con):
            r = prune.podar(self.con, self.cfg)
        c = obtener_combinacion(self.con, 1)
        self.assertEqual((c["cadencia_dias"], c["pasadas_sin_nuevas"]), (20, 0))
        self.assertEqual(r["cadencias_duplicadas"], 1)
        with transaccion(self.con):                    # una segunda poda no vuelve a duplicar ni a recuperar
            prune.podar(self.con, self.cfg)
        self.assertEqual(obtener_combinacion(self.con, 1)["cadencia_dias"], 20)

    def test_respeta_la_cadencia_maxima(self):
        self.con.execute("UPDATE combinaciones SET cadencia_dias = 25, pasadas_sin_nuevas = 3, ultima_ejecucion = '2026-10-01T00:00:00Z' WHERE combinacion_id = 1")
        with transaccion(self.con):
            prune.podar(self.con, self.cfg)
        self.assertEqual(obtener_combinacion(self.con, 1)["cadencia_dias"], 30)

    def test_recupera_la_cadencia_si_vuelve_a_dar_ofertas_nuevas(self):
        self.con.execute("UPDATE combinaciones SET cadencia_dias = 30, ultima_ejecucion = '2026-10-01T00:00:00Z' WHERE combinacion_id = 1")
        cid = consultas_repo.registrar(self.con, 1, 1, 30, "2026-10-01T00:00:00Z", "ok", 5)
        consultas_repo.fijar_nuevos(self.con, cid, 2)
        with transaccion(self.con):
            r = prune.podar(self.con, self.cfg)
        self.assertEqual(obtener_combinacion(self.con, 1)["cadencia_dias"], 10)
        self.assertEqual(r["recuperadas"], 1)

    def test_ubicacion_sin_resultados_en_tres_terminos_se_espacia(self):
        frase = self.cfg.ubicaciones[0].frase
        ids = [r[0] for r in self.con.execute(
            "SELECT combinacion_id FROM combinaciones WHERE ubicacion_frase = ? AND prioridad = 1 ORDER BY combinacion_id LIMIT 3", (frase,))]
        for i in ids:
            consultas_repo.registrar(self.con, i, 1, 30, "2026-10-01T00:00:00Z", "vacia", 0)
        with transaccion(self.con):
            r = prune.podar(self.con, self.cfg)
        self.assertEqual(r["ubicaciones_espaciadas"], 1)
        self.assertEqual(self.con.execute("SELECT DISTINCT cadencia_dias FROM combinaciones WHERE ubicacion_frase = ? AND prioridad = 1", (frase,)).fetchone()[0], 30)


class RitmoPruebas(unittest.TestCase):
    def test_primera_sin_espera_corta_dentro_del_lote_larga_al_cerrarlo(self):
        esperas = []
        r = Ritmo(2, (10, 10), (5, 5), dormir=esperas.append, azar=lambda a, b: a)
        valores = [r.esperar() for _ in range(5)]
        self.assertEqual(valores, [0.0, 10, 300, 10, 300])
        self.assertEqual(esperas, [10, 300, 10, 300])


if __name__ == "__main__":
    unittest.main()
