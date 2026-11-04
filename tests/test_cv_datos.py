"""Comprobación de datos del CV reescrito (nombre, contacto, puestos, formación, certificaciones, idiomas) y raya larga."""
import unittest

from collector.filters.cv import problemas
from collector.filters.cv_datos import verificar_datos
from tests.ayudas import RAIZ, cv_derivado

BASES = ("data_analytics", "mejora_continua", "automation_ai")


def base(nombre="data_analytics"):
    return (RAIZ / "CV" / "base" / f"{nombre}.md").read_text(encoding="utf-8")


class CvReales(unittest.TestCase):
    def test_un_cv_derivado_sin_cambios_de_datos_es_correcto(self):
        for n in BASES:
            with self.subTest(n):
                self.assertEqual(problemas(cv_derivado(n)), [])
                self.assertEqual(verificar_datos(base(n), cv_derivado(n)), [])

    def test_los_logros_se_pueden_reescribir_libremente(self):
        self.assertIn("Diseñé el cuadro de mando mensual", cv_derivado())
        gen = cv_derivado().replace("Diseñé el cuadro de mando mensual", "Monté desde cero el cuadro de mando mensual")
        self.assertEqual(verificar_datos(base(), gen), [])

    def test_omitir_puestos_certificaciones_y_habilidades_es_valido(self):
        gen = cv_derivado().replace("- AWS AI Practitioner Fundamentals (2026)\n", "").replace(" · Docker", "")
        self.assertEqual(verificar_datos(base(), gen), [])

    def test_la_raya_larga_en_logros_se_rechaza_pero_no_en_certificaciones_ni_empresa(self):
        self.assertIn("raya larga", problemas(base())[0])        # el CV base la usa en los logros
        self.assertIn("raya larga", problemas("## PERFIL\n\nTexto — con raya")[0])
        solo_datos = "# N\n\n## CERTIFICACIONES\n\n- Claude Code — Anthropic (2026)\n\n### Puesto\n\nMarca Dos — Madrid | 2024\n"
        self.assertEqual(problemas(solo_datos), [])


class Alteraciones(unittest.TestCase):
    def _fallos(self, viejo, nuevo, nombre="data_analytics"):
        gen = cv_derivado(nombre)
        self.assertIn(viejo, gen)
        return verificar_datos(base(nombre), gen.replace(viejo, nuevo, 1))

    def test_nombre_y_contacto(self):
        self.assertIn("nombre", self._fallos("ANA MARÍA PÉREZ GÓMEZ", "ANA PÉREZ")[0])
        self.assertIn("teléfono", self._fallos("600 111 222", "600 000 000")[0])
        self.assertIn("correo", self._fallos("ana.perez@example.com", "otro@mail.com")[0])
        self.assertTrue(self._fallos("www.linkedin.com/in/ana-perez-ejemplo/", "www.linkedin.com/in/otro/"))

    def test_puesto_empresa_y_fechas(self):
        self.assertEqual(self._fallos("### Ingeniero de Procesos y Organización Digital", "### Data Engineer"), [])
        self.assertIn("fechas", self._fallos("Julio 2025 – Julio 2026", "Julio 2024 – Julio 2026")[0])
        self.assertIn("fechas", self._fallos("Empresa: Empresa Uno España", "Empresa: Otra SL")[0])

    def test_formacion_y_certificaciones(self):
        self.assertIn("estudios", self._fallos("Universidad de Ejemplo (2022) Ingeniería Industrial", "Universidad de Ejemplo (2020) Ingeniería Industrial")[0])
        self.assertIn("certificaciones", self._fallos("MAKE Advanced (2026)", "MAKE Advanced (2025)")[0])
        self.assertIn("certificaciones", self._fallos("- MAKE Advanced (2026)\n", "- MAKE Advanced (2026)\n- Scrum Master (2026)\n")[0])

    def test_las_habilidades_se_pueden_ampliar_con_o_sin_marcador(self):
        self.assertEqual(self._fallos(" · Docker", " · Docker · Kubernetes"), [])
        self.assertEqual(self._fallos(" · Docker", " · Docker · Kubernetes [inferida]"), [])

    def test_el_nivel_de_idioma_no_se_puede_subir(self):
        self.assertIn("idioma «ingles c1»", self._fallos("inglés B2 técnico", "inglés C1")[0])


if __name__ == "__main__":
    unittest.main()
