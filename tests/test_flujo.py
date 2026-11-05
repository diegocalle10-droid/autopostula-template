"""Flujo continuo (pipeline/flujo.py): alterna búsquedas y detalles sin acumular ofertas sin detalle."""
import unittest
from datetime import timedelta
from unittest import mock

from collector.linkedin.errores import LimiteError, LinkedinError
from collector.pipeline import flujo
from collector.pipeline.batch_runner import ResultadoTanda
from tests.ayudas import DESCRIPCION, CliFalso, RelojSimulado, oferta
from tests.base import Base


def _pagina(n, desde=1):
    return [oferta(i, empresa=f"E{i}") for i in range(desde, desde + n)]   # títulos elegibles, huellas distintas


class Flujo(Base):
    def setUp(self):
        super().setUp()
        self.r = RelojSimulado()

    def _flujo(self, cli, n=0, horas=3):
        self.log = []
        return flujo.Flujo(self.con, self.cfg, cli, self.r.ahora, self.r.dormir, fin=self.r.t + timedelta(hours=horas),
                           max_pendientes=n, log=self.log.append)

    def test_con_n_0_el_detalle_va_siempre_antes_de_volver_a_buscar(self):
        cli = CliFalso([_pagina(25), []], {str(i): DESCRIPCION for i in range(1, 26)})
        r = self._flujo(cli).ejecutar()
        self.assertTrue(r.secuencia.startswith("BB" + "D" * 25 + "B"), r.secuencia[:30])   # 25 nuevas: hay página 2
        self.assertEqual(r.detalles, 25)
        self.assertEqual(r.acumulado_max, 25)
        self.assertEqual(r.motivo, "tiempo cumplido")

    def test_las_pausas_son_de_una_peticion_por_minuto(self):
        cli = CliFalso([_pagina(4)], {str(i): DESCRIPCION for i in range(1, 5)})
        self._flujo(cli, horas=1).ejecutar()
        self.assertGreaterEqual(min(self.r.pausas), 60)
        self.assertLessEqual(max(self.r.pausas), 90)

    def test_con_n_mayor_se_toleran_n_ofertas_sin_detalle(self):
        cli = CliFalso([_pagina(25), []], {str(i): DESCRIPCION for i in range(1, 26)})
        r = self._flujo(cli, n=5).ejecutar()
        self.assertTrue(r.secuencia.startswith("BB" + "D" * 20 + "B"), r.secuencia[:30])
        self.assertEqual(r.detalles, 20)                     # las otras 5 esperan a la siguiente búsqueda con datos

    def test_un_429_en_el_detalle_para_el_flujo(self):
        cli = CliFalso([_pagina(3), []], {"1": LimiteError("DETAIL_FAILED", "Request failed: 429")})
        r = self._flujo(cli).ejecutar()
        self.assertTrue(r.limite)
        self.assertIn("429", r.motivo)
        self.assertEqual(r.secuencia, "BD")

    def test_una_oferta_ilegible_se_descarta_y_el_flujo_sigue(self):
        detalles = {str(i): DESCRIPCION for i in range(1, 4)}
        detalles["1"] = {"description": "", "isActive": True}
        r = self._flujo(CliFalso([_pagina(3), []], detalles)).ejecutar()
        self.assertTrue(r.secuencia.startswith("BDDDD"), r.secuencia)   # la 1 dos veces y luego la 2 y la 3
        self.assertEqual(r.detalles, 3)
        self.assertEqual(r.motivo, "tiempo cumplido")
        self.assertEqual(self.con.execute("SELECT motivo_descarte FROM ofertas WHERE job_id = '1'").fetchone()[0],
                         "detalle_ilegible")

    def test_ofertas_ilegibles_seguidas_paran_el_flujo(self):
        vacia = {"description": "", "isActive": True}
        r = self._flujo(CliFalso([_pagina(3), []], {str(i): vacia for i in range(1, 4)})).ejecutar()
        self.assertEqual(r.motivo, "fallos seguidos en el detalle")
        self.assertEqual(r.secuencia, "BDDD")   # la 1 se descarta y la 2 falla: no se vacía la cola por un fallo general

    def test_fallos_seguidos_en_el_detalle_paran_y_pausan(self):
        error = LinkedinError("DETAIL_FAILED", "error raro")
        cli = CliFalso([_pagina(3), []], {str(i): error for i in range(1, 4)})
        r = self._flujo(cli).ejecutar()
        self.assertEqual(r.motivo, "fallos seguidos en el detalle")
        self.assertEqual(r.secuencia, "BDDD")

    def test_con_la_agenda_agotada_se_vacian_los_detalles_y_termina(self):
        self.tanda(CliFalso([_pagina(3)]), 1)                 # 3 ofertas elegibles ya guardadas
        cli = CliFalso(detalles={str(i): DESCRIPCION for i in range(1, 4)})
        with mock.patch.object(flujo, "ejecutar_tanda", return_value=ResultadoTanda(detenida_por=flujo.AGENDA_VACIA)):
            r = self._flujo(cli, n=5).ejecutar()            # con n=5 no se detallarían sin agenda agotada
        self.assertEqual(r.secuencia, "DDD")
        self.assertEqual(r.motivo, "agenda agotada y sin detalles pendientes")

    def test_el_resumen_da_el_reparto(self):
        cli = CliFalso([_pagina(4)], {str(i): DESCRIPCION for i in range(1, 5)})
        texto = flujo.resumen(self._flujo(cli, horas=0.5).ejecutar())
        self.assertIn("detalles evaluados por búsqueda", texto)
        self.assertIn("acumulado máximo", texto)


if __name__ == "__main__":
    unittest.main()
