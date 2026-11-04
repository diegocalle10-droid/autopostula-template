"""Clase base de las pruebas de pipeline: configuración real, base en memoria y agenda cargada."""
import unittest

from collector.db.connection import transaccion
from collector.pipeline import plan_builder
from collector.pipeline.batch_runner import ejecutar_tanda
from tests.ayudas import base_en_memoria, config, reloj_fijo, sin_pausas


class Base(unittest.TestCase):
    def setUp(self):
        self.cfg = config()
        self.con = base_en_memoria()
        self.addCleanup(self.con.close)
        self.reloj = reloj_fijo()
        with transaccion(self.con):
            plan_builder.sincronizar(self.con, self.cfg, self.reloj())

    def tanda(self, cli, maximo=3):
        return ejecutar_tanda(self.con, self.cfg, cli, sin_pausas(), self.reloj, maximo)
