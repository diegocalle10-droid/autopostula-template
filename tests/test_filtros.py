import unittest

from collector.filters.evaluar import evaluar
from collector.filters.huella import huella
from collector.filters.idioma import idioma_de_texto, idioma_de_titulo, nivel_idioma
from collector.filters.keywords import keywords_en
from collector.filters.pais import pais_de_oferta
from collector.util.md_tables import clave
from collector.util.texto import hay_negacion_previa, normalizar
from tests.ayudas import config

CFG = config()
ES = ("Buscamos un analista con experiencia en el área de datos para trabajar con nuestro equipo en la "
      "construcción de informes y la mejora de los procesos de la empresa.")
EN = ("We are looking for an analyst with experience in the data area to work with our team on the "
      "reports and the improvement of the processes of the company.")


class Util(unittest.TestCase):
    def test_clave(self):
        self.assertEqual(clave("Países aceptados"), "paises_aceptados")
        self.assertEqual(clave("Reserva (capitales y siglas)"), "reserva_capitales_y_siglas")

    def test_normalizar_quita_acentos_y_pone_fin_de_frase_en_saltos(self):
        self.assertEqual(normalizar("Inglés  Técnico\nHíbrido"), "ingles tecnico. hibrido")

    def test_la_negacion_no_cruza_frases(self):
        t = normalizar("No hay problema. Modalidad hibrido")
        self.assertFalse(hay_negacion_previa(t, t.index("hibrido"), ["no hay"], 30))


class Idioma(unittest.TestCase):
    def test_texto(self):
        self.assertEqual(idioma_de_texto(ES, CFG.idioma), "es")
        self.assertEqual(idioma_de_texto(EN, CFG.idioma), "en")
        self.assertEqual(idioma_de_texto(ES + " " + EN, CFG.idioma), "mixto")
        self.assertIsNone(idioma_de_texto("Hola", CFG.idioma))

    def test_titulo(self):
        self.assertEqual(idioma_de_titulo("Analista de datos", CFG.idioma), "es")
        self.assertEqual(idioma_de_titulo("Data Analyst", CFG.idioma), "en")
        self.assertEqual(idioma_de_titulo("Power BI Developer", CFG.idioma), "en")
        self.assertEqual(idioma_de_titulo("Analista BI", CFG.idioma), "es")

    def test_nivel_idioma(self):
        casos = {
            "Se valora inglés técnico": "aceptable",
            "Nivel B2 de inglés": "aceptable",
            "Se requiere inglés avanzado": "exigente",
            "Imprescindible nivel C1 de English": "exigente",
            "No se requiere inglés avanzado": "aceptable",
            "Versión B2 del producto": "ninguno",       # B2 sin «inglés» cerca no cuenta
            "Inglés intermedio, se valora inglés avanzado": "dudoso",
            "Trabajo con Excel": "ninguno",
        }
        for texto, esperado in casos.items():
            with self.subTest(texto):
                self.assertEqual(nivel_idioma(texto, CFG.idioma), esperado)


class Evaluacion(unittest.TestCase):
    def _ev(self, titulo, descripcion, activa=True, modalidad=None):
        return evaluar(titulo, descripcion, activa, CFG, modalidad=modalidad)

    def test_anuncio_en_espanol_con_etiqueta_remoto_es_apta(self):
        e = self._ev("Analista de datos", ES + " Se valora inglés técnico.", modalidad="remoto")
        self.assertEqual((e.estado, e.nivel_idioma, e.modalidad_detectada), ("apta", "aceptable", "remoto"))

    def test_sin_etiqueta_vale_la_modalidad_con_la_que_se_busco(self):
        e = self._ev("Analista de datos", ES)
        self.assertEqual((e.estado, e.motivo_descarte, e.modalidad_detectada), ("apta", None, None))

    def test_la_descripcion_ya_no_decide_la_modalidad(self):
        for frase in ("Trabajo híbrido.", "Modalidad presencial.", "Hybrid role."):
            with self.subTest(frase):
                self.assertEqual(self._ev("Analista de datos", ES + " " + frase).estado, "apta")

    def test_titulo_en_ingles_con_anuncio_en_espanol_no_descarta(self):
        self.assertEqual(self._ev("Data Analyst", ES, modalidad="remoto").estado, "apta")

    def test_ingles_exigente_descarta(self):
        e = self._ev("Analista de datos", ES + " Imprescindible inglés avanzado.")
        self.assertEqual((e.estado, e.motivo_descarte), ("descartada", "ingles_exigente"))

    def test_anuncio_en_ingles_sin_glosario_descarta(self):
        e = self._ev("Data Analyst", EN)
        self.assertEqual((e.estado, e.motivo_descarte), ("descartada", "idioma_en_sin_glosario"))

    def test_anuncio_en_ingles_con_ingles_aceptable_va_a_revisar(self):
        self.assertEqual(self._ev("Data Analyst", EN + " Intermediate English.").estado, "revisar")

    def test_contenido_mixto_no_se_descarta(self):
        self.assertEqual(self._ev("Analista de datos", ES + " " + EN, modalidad="remoto").estado, "apta")

    def test_otra_modalidad_descarta(self):
        for modalidad in ("hibrido", "presencial"):
            with self.subTest(modalidad):
                e = self._ev("Analista de datos", ES, modalidad=modalidad)
                self.assertEqual((e.estado, e.motivo_descarte, e.modalidad_detectada), ("descartada", f"modalidad:{modalidad}", modalidad))

    def test_cerrada_descarta(self):
        self.assertEqual(self._ev("Analista de datos", ES, activa=False).motivo_descarte, "cerrada")

    def test_keywords_salen_de_inputs(self):
        e = self._ev("Analista de datos", ES + " Dominio de Power BI y n8n.")
        self.assertIn("power bi", e.keywords)
        self.assertIn("n8n", e.keywords)
        self.assertNotIn("uipath", e.keywords)


class PaisYHuella(unittest.TestCase):
    A, X = CFG.paises_aceptados, CFG.paises_excluidos

    def test_pais(self):
        c = lambda ub, pais: pais_de_oferta(ub, self.A, self.X, pais)
        self.assertEqual(c("Bogotá, Colombia", "Colombia"), ("Colombia", "aceptado"))
        self.assertEqual(c("Madrid, Community of Madrid, Spain", None), ("Spain", "excluido"))   # España, retirada
        self.assertEqual(c("Santiago Metropolitan Area", "Chile"), ("Chile", "aceptado"))
        self.assertEqual(c("Sao Paulo, Brazil", None), ("Brazil", "excluido"))
        self.assertEqual(c("Mexico", None), ("Mexico", "aceptado"))
        self.assertEqual(c("Latin America", None), ("Latin America", "aceptado"))

    def test_busqueda_de_una_ciudad_atribuye_su_pais(self):
        self.assertEqual(pais_de_oferta("Greater Bogotá Metropolitan Area", self.A, self.X, "Colombia"), ("Colombia", "aceptado"))

    def test_lugar_no_reconocido_en_busqueda_regional_no_se_descarta(self):
        self.assertEqual(pais_de_oferta("Greater Madrid Metropolitan Area", self.A, self.X, None),
                         (None, "desconocido"))
        self.assertEqual(pais_de_oferta(None, self.A, self.X, None), (None, "desconocido"))

    def test_huella(self):
        self.assertEqual(huella("Acme", "Analista de Datos", "Madrid"), huella("ACME ", "analista de datos", "madrid"))
        self.assertNotEqual(huella("Acme", "Analista", "Madrid"), huella("Acme", "Analista", "Lima"))

    def test_keywords_sin_duplicados(self):
        self.assertEqual(keywords_en("power bi y Power BI", ["power bi", "power bi"]), ["power bi"])


if __name__ == "__main__":
    unittest.main()
