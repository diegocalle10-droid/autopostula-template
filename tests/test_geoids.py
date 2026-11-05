"""geo_id de las ubicaciones: carga, escritura en ubicaciones.md, criterio de fiabilidad y aviso antes de ejecutar."""
import contextlib
import io
import unittest
from dataclasses import replace

from collector.comandos.ejecucion import _sin_geo_id
from collector.config.cargar import _geo_id
from collector.config.modelos import ConfigError
from collector.config.ubicaciones_md import fijar_geo_id
from collector.linkedin.geoids import fiable
from tests.ayudas import config

MD = """## Países

| tipo | frase | pais_esperado | geo_id | nota |
|---|---|---|---|---|
| pais | Mexico | Mexico | - |  |
| pais | Peru | Peru | - | otra nota |

## Otra

| tipo | frase | pais_esperado | nota |
|---|---|---|---|
| sigla | MX | Mexico | sin columna geo_id |"""


class Carga(unittest.TestCase):
    def test_las_ubicaciones_reales_tienen_geo_id(self):
        self.assertTrue(all(u.geo_id and u.geo_id.isdigit() for u in config().ubicaciones))

    def test_vacio_o_guion_es_sin_resolver_y_un_texto_es_error(self):
        self.assertIsNone(_geo_id("-", "Mexico"))
        self.assertIsNone(_geo_id("", "Mexico"))
        self.assertEqual(_geo_id("103323778", "Mexico"), "103323778")
        with self.assertRaises(ConfigError):
            _geo_id("Mexico", "Mexico")


class Escritura(unittest.TestCase):
    def test_fija_solo_la_celda_de_esa_fila(self):
        nuevo = fijar_geo_id(MD, "Peru", "102927786")
        self.assertIn("| pais | Peru | Peru | 102927786 | otra nota |", nuevo)
        self.assertIn("| pais | Mexico | Mexico | - |  |", nuevo)
        self.assertEqual(len(nuevo.split("\n")), len(MD.split("\n")))

    def test_frase_inexistente_o_en_tabla_sin_geo_id_es_error(self):
        for frase in ("Chile", "MX"):
            with self.subTest(frase), self.assertRaises(ValueError):
                fijar_geo_id(MD, frase, "1")


class Fiabilidad(unittest.TestCase):
    def test_pais_entero_es_fiable(self):
        self.assertTrue(fiable({"geo_id": "105057336", "opciones": ["República Dominicana"], "desplegable": "República Dominicana"}))

    def test_un_lugar_parcial_o_sin_sugerencias_no(self):
        sa = {"geo_id": "116291524", "opciones": ["American River, Australia Meridional, Australia"],
              "desplegable": "American River, SA (80 km)"}
        self.assertFalse(fiable(sa))
        self.assertFalse(fiable({"geo_id": None, "opciones": [], "desplegable": ""}))


class AvisoPrevio(unittest.TestCase):
    def test_sin_geo_id_no_se_ejecuta(self):
        cfg = config()
        self.assertFalse(_sin_geo_id(cfg))
        sin = replace(cfg, ubicaciones=[replace(cfg.ubicaciones[0], geo_id=None)] + cfg.ubicaciones[1:])
        with contextlib.redirect_stdout(io.StringIO()) as salida:
            self.assertTrue(_sin_geo_id(sin))
        self.assertIn("geoids --escribir", salida.getvalue())
