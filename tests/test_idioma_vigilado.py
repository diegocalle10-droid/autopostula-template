"""Glosarios de configurar/: con idioma propio inglés y vigilado español, el filtro de nivel funciona igual."""
import shutil
import tempfile
import unittest
from pathlib import Path

from collector.config.cargar import cargar_config
from collector.filters.idioma import idioma_de_texto, nivel_idioma
from tests.ayudas import PROYECTO, RAIZ


def _con_vigilado(codigo: str, propio: str) -> Path:
    """Copia de los inputs de ejemplo con el glosario de configurar/ del idioma `codigo`, como hace la entrevista."""
    inputs = Path(tempfile.mkdtemp()) / "inputs"
    shutil.copytree(RAIZ / "inputs", inputs)
    idioma = (inputs / "idioma.md").read_text(encoding="utf-8")
    glosario = (PROYECTO / "configurar" / f"idioma_vigilado_{codigo}.md").read_text(encoding="utf-8")
    inicio, fin = idioma.index("## Alias del idioma vigilado"), idioma.index("## Niveles MCER")
    idioma = idioma[:inicio] + glosario[glosario.index("## Alias"):] + idioma[fin:]
    idioma = idioma.replace("| idioma_propio | es |", f"| idioma_propio | {propio} |")
    idioma = idioma.replace("| idioma_vigilado | en |", f"| idioma_vigilado | {codigo} |")
    (inputs / "idioma.md").write_text(idioma, encoding="utf-8")
    return inputs


class VigiladoEspanol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        inputs = _con_vigilado("es", "en")
        cls.addClassCleanup(shutil.rmtree, inputs.parent)
        cls.cfg = cargar_config(inputs).idioma

    def test_niveles(self):
        self.assertEqual(nivel_idioma("Data analyst. Fluent Spanish is required.", self.cfg), "exigente")
        self.assertEqual(nivel_idioma("Data analyst, Spanish is a plus.", self.cfg), "aceptable")
        self.assertEqual(nivel_idioma("Analyst, Spanish C1 needed", self.cfg), "exigente")
        self.assertEqual(nivel_idioma("Analyst with Spanish B1", self.cfg), "aceptable")

    def test_un_anuncio_en_ingles_es_el_idioma_propio(self):
        texto = "We are looking for an analyst to join our team and work with the data of our clients"
        self.assertEqual(idioma_de_texto(texto, self.cfg), "en")


class GlosarioIngles(unittest.TestCase):
    def test_la_plantilla_inglesa_carga(self):
        inputs = _con_vigilado("en", "es")
        self.addCleanup(shutil.rmtree, inputs.parent)
        self.assertEqual(nivel_idioma("Se requiere inglés fluido", cargar_config(inputs).idioma), "exigente")
