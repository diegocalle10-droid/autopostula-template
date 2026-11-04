"""Puesta en marcha: qué se reconoce de un CV base y qué le falta para servir."""
import unittest

import shutil
import tempfile
from argparse import Namespace
from pathlib import Path

from collector.comandos import instalacion
from collector.filters.cv_datos import faltas_de_ficha, ficha
from tests.ayudas import RAIZ


class FichaDelCv(unittest.TestCase):
    def test_un_cv_completo_no_tiene_faltas(self):
        d = ficha((RAIZ / "CV" / "base" / "data_analytics.md").read_text(encoding="utf-8"))
        self.assertEqual(d["correo"], ["ana.perez@example.com"])
        self.assertGreater(d["puestos"], 0)
        self.assertEqual(faltas_de_ficha(d), [])

    def test_un_cv_sin_cabecera_ni_puestos_dice_que_falta(self):
        faltas = faltas_de_ficha(ficha("## PERFIL\n\nTexto suelto\n\n### Cargo\n\n- Logro\n"))
        self.assertEqual(len(faltas), 4)   # nombre, correo, puesto con empresa y fechas, formación


class EntrevistaPorPartes(unittest.TestCase):
    def test_validar_cv_funciona_con_el_resto_de_inputs_vacio(self):
        inputs = Path(tempfile.mkdtemp()) / "inputs"
        self.addCleanup(shutil.rmtree, inputs.parent)
        shutil.copytree(RAIZ / "inputs", inputs)
        (inputs / "ubicaciones.md").write_text("# vacío\n", encoding="utf-8")   # como en el paso 1 de la entrevista
        self.assertEqual(instalacion.validar_cv(Namespace(inputs=str(inputs), raiz=str(RAIZ))), 0)
