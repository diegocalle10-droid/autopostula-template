"""CV a medida: reglas de texto, configuración y generación del PDF."""
import shutil
import tempfile
import unittest
from pathlib import Path

from collector.config.cargar import cargar_config
from collector.config.modelos import ConfigError
from collector.cv.render import bloques, generar_pdf
from collector.filters.cv import nombre_pdf, problemas, quitar_marcadores, slug
from tests.ayudas import RAIZ

AHORA = "2026-10-28T12:00:00Z"
CV_MD = "# NOMBRE APELLIDO\n\nAnalista · Madrid\n\n## PERFIL\n\nTexto del perfil con **negrita** & símbolos <b>.\n\n" \
        "## EXPERIENCIA\n\n### Cargo\n\nEmpresa | 2024 - 2025\n\n- Logro uno [inferida]\n- Logro dos\n"


class Texto(unittest.TestCase):
    def test_los_marcadores_inferida_se_quitan(self):
        self.assertEqual(quitar_marcadores("- Dato [inferida]\n- Otro [INFERIDA] más"), "- Dato\n- Otro más")

    def test_la_raya_larga_y_el_archivo_vacio_son_defectos(self):
        self.assertEqual(problemas("Hola, bien escrito."), [])
        self.assertTrue(problemas("Texto — con raya"))
        self.assertEqual(problemas("# N\n\n## CERTIFICACIONES\n\n- Claude Code — Anthropic (2026)\n"), [])   # separador legítimo

    def test_los_marcadores_y_placeholders_sin_resolver_son_defectos(self):
        self.assertEqual(problemas("- Habilidad [inferida]\n"), [])     # lo interno se quita antes de entregar
        for texto in ("Contacto: [teléfono]", "Hola {{nombre}}", "- Logro <pendiente>", "TODO completar", "XXX"):
            with self.subTest(texto):
                self.assertIn("plantilla", problemas(texto)[0])
        self.assertEqual(problemas("Todo el equipo, texto normal."), [])   # «todo» en minúscula no es un marcador
        self.assertTrue(problemas("  \n"))

    def test_nombre_del_pdf_es_el_titulo_de_la_vacante(self):
        self.assertEqual(nombre_pdf("CV -", "Business Analyst"), "CV - Business Analyst.pdf")
        self.assertEqual(nombre_pdf("CV -", 'Analista: BI / Datos (Madrid)?  '), "CV - Analista BI Datos (Madrid).pdf")
        self.assertEqual(nombre_pdf("CV -", ""), "CV.pdf")
        self.assertLessEqual(len(nombre_pdf("CV -", "x" * 300)), 100 + 9)

    def test_slug(self):
        self.assertEqual(slug("Acme S.L. (Madrid)"), "acme-s-l-madrid")
        self.assertEqual(slug(""), "sin-nombre")
        self.assertLessEqual(len(slug("x" * 100)), 40)

    def test_bloques_separa_cabecera_y_secciones(self):
        tipos = [t for t, _ in bloques(CV_MD)]
        self.assertEqual(tipos, ["h1", "cabecera", "h2", "p", "h2", "h3", "p", "li", "li"])


class Pdf(unittest.TestCase):
    def test_genera_un_pdf_de_texto_seleccionable(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "sub" / "CV.pdf"
            paginas, _ = generar_pdf(quitar_marcadores(CV_MD), ruta, "CV prueba")
            contenido = ruta.read_bytes()
        self.assertEqual(paginas, 1)
        self.assertTrue(contenido.startswith(b"%PDF"))

    def test_un_cv_largo_reduce_la_letra_hasta_caber_en_dos_paginas(self):
        largo = CV_MD + "\n".join(f"- Logro numero {i} con texto suficiente para ocupar una linea completa del documento" for i in range(100))
        with tempfile.TemporaryDirectory() as d:
            paginas, tam = generar_pdf(largo, Path(d) / "CV.pdf")
        self.assertLessEqual(paginas, 2)
        self.assertLess(tam, 10.0)


class Configuracion(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.inputs = Path(self.dir.name) / "inputs"
        shutil.copytree(RAIZ / "inputs", self.inputs)

    def _editar(self, viejo, nuevo):
        ruta = self.inputs / "cv.md"
        ruta.write_text(ruta.read_text(encoding="utf-8").replace(viejo, nuevo, 1), encoding="utf-8")

    def test_la_configuracion_real_carga(self):
        cfg = cargar_config(self.inputs)
        self.assertEqual(cfg.cv.umbral_afinidad, 35)
        self.assertIsNotNone(cfg.cv.cv("data_analytics"))

    def test_umbral_fuera_de_rango(self):
        self._editar("| umbral_afinidad | 35 |", "| umbral_afinidad | 150 |")
        with self.assertRaisesRegex(ConfigError, "entre 0 y 100"):
            cargar_config(self.inputs)

    def test_los_cv_base_reales_existen(self):
        for c in cargar_config(RAIZ / "inputs").cv.cvs:
            self.assertTrue((RAIZ / c.archivo).is_file(), c.archivo)


if __name__ == "__main__":
    unittest.main()
