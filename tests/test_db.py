import sqlite3
import unittest

from collector.db import combinaciones_repo, ofertas_repo
from collector.db.connection import conectar
from collector.db.migrar import migrar, version_actual
from tests.ayudas import base_en_memoria, obtener_combinacion

AHORA = "2026-10-28T12:00:00Z"


def fila(job_id="1", **extra):
    base = {"job_id": job_id, "url": "u", "titulo": "t", "empresa": "e", "ubicacion": "Spain", "pais": "Spain",
            "fecha_publicacion": "2026-10-20", "modalidad": "remoto", "estado": "pendiente",
            "motivo_descarte": None, "huella": "h", "duplicada_de": None}
    base.update(extra)
    return base


class Migraciones(unittest.TestCase):
    def test_se_aplican_una_vez(self):
        con = conectar(":memory:")
        self.addCleanup(con.close)
        self.assertEqual(migrar(con), [1])
        self.assertEqual(version_actual(con), 1)
        self.assertEqual(migrar(con), [])   # idempotente


class Ofertas(unittest.TestCase):
    def setUp(self):
        self.con = base_en_memoria()
        self.addCleanup(self.con.close)

    def test_no_duplica_por_job_id(self):
        self.assertTrue(ofertas_repo.insertar_nueva(self.con, fila("1"), AHORA))
        self.assertFalse(ofertas_repo.insertar_nueva(self.con, fila("1"), AHORA))
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM ofertas").fetchone()[0], 1)

    def test_descartada_exige_motivo(self):
        ofertas_repo.insertar_nueva(self.con, fila("1"), AHORA)
        with self.assertRaises(sqlite3.IntegrityError):
            ofertas_repo.descartar(self.con, "1", None)

    def test_buscar_original_por_huella(self):
        ofertas_repo.insertar_nueva(self.con, fila("1", huella="x"), AHORA)
        self.assertEqual(ofertas_repo.buscar_original_por_huella(self.con, "x", "2", "2026-09-01T00:00:00Z"), "1")
        self.assertIsNone(ofertas_repo.buscar_original_por_huella(self.con, "x", "1", "2026-09-01T00:00:00Z"))
        self.assertIsNone(ofertas_repo.buscar_original_por_huella(self.con, "x", "2", "2026-12-01T00:00:00Z"))

    def test_pendientes_son_las_que_no_tienen_detalle(self):
        ofertas_repo.insertar_nueva(self.con, fila("1"), AHORA)
        ofertas_repo.insertar_nueva(self.con, fila("2"), AHORA)
        ofertas_repo.descartar(self.con, "2", "cerrada", AHORA)
        self.assertEqual([o["job_id"] for o in ofertas_repo.pendientes_de_detalle(self.con)], ["1"])

    def test_descartar_con_ahora_cuenta_como_detalle(self):
        ofertas_repo.insertar_nueva(self.con, fila("1"), AHORA)
        ofertas_repo.descartar(self.con, "1", "cerrada", AHORA)
        self.assertEqual(ofertas_repo.contar_detalles_desde(self.con, "2026-10-28T00:00:00Z"), 1)
        self.assertEqual(ofertas_repo.pendientes_de_detalle(self.con), [])


class Combinaciones(unittest.TestCase):
    def test_sincronizar_no_pisa_cadencia_podada_y_retira_las_que_faltan(self):
        con = base_en_memoria()
        self.addCleanup(con.close)
        combinaciones_repo.sincronizar(con, [("a", "Spain", 1, 10), ("b", "Spain", 2, 30)], AHORA)
        combinaciones_repo.fijar_cadencia(con, 1, 30)
        r = combinaciones_repo.sincronizar(con, [("a", "Spain", 1, 10)], AHORA)
        self.assertEqual((r["nuevas"], r["retiradas"]), (0, 1))
        self.assertEqual(obtener_combinacion(con, 1)["cadencia_dias"], 30)
        self.assertEqual(combinaciones_repo.contar(con), {"total": 2, "activas": 1})


if __name__ == "__main__":
    unittest.main()



class CambioDePrioridad(unittest.TestCase):
    def test_subir_un_termino_de_prioridad_le_pone_su_cadencia_y_lo_deja_pendiente_ya(self):
        con = base_en_memoria()
        self.addCleanup(con.close)
        combinaciones_repo.sincronizar(con, [("a", "Mexico", 2, 20)], AHORA)
        con.execute("UPDATE combinaciones SET proxima_ejecucion = '2999-01-01T00:00:00Z'")
        combinaciones_repo.sincronizar(con, [("a", "Mexico", 1, 10)], "2026-11-01T08:00:00Z")
        f = con.execute("SELECT prioridad, cadencia_dias, proxima_ejecucion FROM combinaciones").fetchone()
        self.assertEqual(tuple(f), (1, 10, "2026-11-01T08:00:00Z"))

    def test_sin_cambio_de_prioridad_no_se_toca_la_cadencia_podada(self):
        con = base_en_memoria()
        self.addCleanup(con.close)
        combinaciones_repo.sincronizar(con, [("a", "Mexico", 1, 10)], AHORA)
        con.execute("UPDATE combinaciones SET cadencia_dias = 40")
        combinaciones_repo.sincronizar(con, [("a", "Mexico", 1, 10)], "2026-11-01T08:00:00Z")
        self.assertEqual(con.execute("SELECT cadencia_dias FROM combinaciones").fetchone()[0], 40)
