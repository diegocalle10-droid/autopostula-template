"""La misma vacante publicada en varias ubicaciones (misma empresa y descripción, job_id distintos)."""
import unittest

from collector.db import ofertas_repo
from collector.db.connection import transaccion
from collector.pipeline.detail_runner import procesar_detalles
from tests.ayudas import CliFalso, oferta, sin_pausas
from tests.base import Base
from tests.test_pipeline import ES


def detalle(texto=ES):
    return {"description": texto, "employmentType": "Full-time", "isActive": True}


class PorContenido(Base):
    def setUp(self):
        super().setUp()
        self.tanda(CliFalso([[oferta(1, ubicacion="Bogota, Colombia"), oferta(2, ubicacion="Lima, Peru")]]), 1)

    def estado(self, job_id):
        return tuple(self.con.execute("SELECT estado, motivo_descarte, duplicada_de FROM ofertas WHERE job_id = ?",
                                      (job_id,)).fetchone())

    def test_la_copia_en_otra_ubicacion_queda_duplicada_de_la_primera(self):
        procesar_detalles(self.con, self.cfg, CliFalso(detalles={"1": detalle(), "2": detalle("  " + ES.upper())}),
                          sin_pausas(), self.reloj, 5)
        self.assertNotEqual(self.estado("1")[0], "descartada")
        self.assertEqual(self.estado("2"), ("descartada", "duplicada_de:1", "1"))

    def test_otra_descripcion_no_es_duplicada(self):
        procesar_detalles(self.con, self.cfg, CliFalso(detalles={"1": detalle(), "2": detalle(ES + " Otra vacante.")}),
                          sin_pausas(), self.reloj, 5)
        self.assertIsNone(self.estado("2")[2])

    def test_limpieza_conserva_la_mas_antigua_y_borra_el_resto(self):
        for job_id in ("1", "2"):
            self.con.execute("UPDATE ofertas SET descripcion = ?, estado = 'apta' WHERE job_id = ?", (ES, job_id))
        grupos = ofertas_repo.grupos_por_contenido(self.con)
        self.assertEqual([[f["job_id"] for f in g] for g in grupos], [["1", "2"]])
        self.con.execute("DELETE FROM sync_pendientes")
        with transaccion(self.con):
            ofertas_repo.borrar_copias(self.con, "1", ["2"])
        self.assertEqual([r[0] for r in self.con.execute("SELECT job_id FROM ofertas")], ["1"])
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM hallazgos WHERE job_id = '2'").fetchone()[0], 0)
        cola = {tuple(f) for f in self.con.execute("SELECT tabla, k1 FROM sync_pendientes")}
        self.assertIn(("ofertas", "2"), cola)   # el borrado viaja a Neon
        self.assertEqual(ofertas_repo.grupos_por_contenido(self.con), [])


if __name__ == "__main__":
    unittest.main()
