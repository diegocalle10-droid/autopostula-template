"""Fallo de unas combinaciones o de todo el sistema: búsquedas de control y parada sin plazo (pipeline/control.py)."""
from datetime import timedelta

from collector.db import eventos_repo
from collector.db.connection import transaccion
from collector.linkedin.errores import LinkedinError
from collector.pipeline import breaker
from collector.util.reloj import a_iso
from tests.ayudas import CliFalso, oferta
from tests.base import Base

class Control(Base):
    """Fallo de unas combinaciones o de todo el sistema: búsquedas de control y parada sin plazo."""
    FALLO = LinkedinError("SEARCH_FAILED", "Request failed: 500")

    def setUp(self):
        super().setUp()
        self.tanda(CliFalso([[oferta(1)]]), 1)   # la combinación 1 trajo ofertas: sirve de control

    def test_los_vacios_que_confirma_linkedin_no_paran(self):
        r = self.tanda(CliFalso([[], [], [], [], []]), 5)
        self.assertEqual(r.consultas, 5)
        self.assertIsNone(eventos_repo.pausa_activa(self.con, a_iso(self.reloj())))

    def test_tres_combinaciones_fallidas_y_controles_fallidos_paran_sin_plazo(self):
        cli = CliFalso([self.FALLO] * 4)
        r = self.tanda(cli, 10)
        self.assertEqual(r.consultas, 4)                                  # 3 combinaciones + 1 control (solo hay uno)
        self.assertIn("control", r.detenida_por)
        self.assertEqual(cli.llamadas[-1][1:3], (self.cfg.terminos[0].termino, self.cfg.ubicaciones[0].frase))
        p = eventos_repo.pausa_activa(self.con, a_iso(self.reloj() + timedelta(days=400)))
        self.assertEqual(p["pausa_hasta"], breaker.SIN_PLAZO)

    def test_si_un_control_trae_lista_se_sigue(self):
        r = self.tanda(CliFalso([self.FALLO, self.FALLO, self.FALLO, [oferta(5)], [oferta(6)]]), 5)
        self.assertEqual(r.consultas, 5)
        self.assertIsNone(r.detenida_por)
        self.assertIsNone(eventos_repo.pausa_activa(self.con, a_iso(self.reloj())))

    def test_al_arrancar_un_control_que_trae_lista_levanta_la_parada(self):
        with transaccion(self.con):
            breaker.parar_por_sospecha(self.con, self.reloj(), "prueba")
        cli = CliFalso([[oferta(7)], [oferta(8)]])
        r = self.tanda(cli, 2)
        self.assertEqual(len(cli.llamadas), 2)                            # el control y una combinación normal
        self.assertIsNone(breaker.hay_parada_por_sospecha(self.con, self.reloj()))
        self.assertIsNone(r.detenida_por)

    def test_al_arrancar_un_control_sin_lista_mantiene_la_parada(self):
        with transaccion(self.con):
            breaker.parar_por_sospecha(self.con, self.reloj(), "prueba")
        cli = CliFalso([self.FALLO])
        r = self.tanda(cli, 5)
        self.assertEqual(len(cli.llamadas), 1)
        self.assertIn("sigue parada", r.detenida_por)
        self.assertIsNotNone(breaker.hay_parada_por_sospecha(self.con, self.reloj()))

    def test_con_un_429_vigente_no_se_hace_el_control(self):
        with transaccion(self.con):
            breaker.parar_por_sospecha(self.con, self.reloj(), "prueba")
            breaker.registrar_limite(self.con, self.cfg, self.reloj(), "x")
        cli = CliFalso([[oferta(7)]])
        self.tanda(cli, 2)
        self.assertEqual(cli.llamadas, [])

    def test_reanudar_levanta_la_parada_por_sospecha(self):
        with transaccion(self.con):
            breaker.parar_por_sospecha(self.con, self.reloj(), "prueba")
            self.assertEqual(eventos_repo.cancelar_pausas(self.con, a_iso(self.reloj())), 1)
        self.assertIsNone(breaker.hay_parada_por_sospecha(self.con, self.reloj()))
