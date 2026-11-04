"""inputs/mensajes/: validación al arrancar, textos fuera del código, cierre de la captura y apagado del PC. Sin red."""
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from collector.config import textos
from collector.config.cargar import cargar_config
from collector.config.modelos import ConfigError
from collector.online import mensajes
from collector.util import apagado
from tests.ayudas import RAIZ


class Validacion(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.inputs = Path(self.dir.name)
        shutil.copytree(RAIZ / "inputs", self.inputs, dirs_exist_ok=True)

    def _editar(self, viejo, nuevo):
        for ruta in (self.inputs / "mensajes").glob("*.md"):
            texto = ruta.read_text(encoding="utf-8")
            if viejo in texto:
                ruta.write_text(texto.replace(viejo, nuevo, 1), encoding="utf-8")
                return
        raise AssertionError(f"no está en inputs/mensajes/: {viejo}")

    def test_el_archivo_real_es_valido_y_lo_carga_la_configuracion(self):
        cargar_config(RAIZ / "inputs")
        self.assertEqual(textos.cargar(RAIZ / "inputs").ajustes["zona_horaria"], "Europe/Madrid")

    def test_un_marcador_desconocido_falla(self):
        self._editar("Nada por redactar hoy {dia}", "Nada por redactar hoy {fecha}")
        with self.assertRaisesRegex(ConfigError, "nada_por_redactar.*fecha"):
            cargar_config(self.inputs)

    def test_un_mensaje_de_oferta_sin_job_id_falla(self):
        self._editar("\\nID: {job_id}\\nAfinidad", "\\nAfinidad")
        self._editar("genera el CV para {job_id}", "genera el CV")
        with self.assertRaisesRegex(ConfigError, "sin_cv.*job_id"):
            cargar_config(self.inputs)

    def test_falta_una_plantilla_o_un_ajuste(self):
        self._editar("| nada_por_redactar |", "| otra_cosa |")
        with self.assertRaisesRegex(ConfigError, "nada_por_redactar"):
            textos.cargar(self.inputs)
        self._editar("| otra_cosa |", "| nada_por_redactar |")
        self._editar("| presupuesto_vinetas | 3000 |", "| presupuesto_vinetas | tres mil |")
        with self.assertRaisesRegex(ConfigError, "presupuesto_vinetas"):
            textos.cargar(self.inputs)

    def test_una_clave_repetida_en_dos_archivos_falla(self):
        with open(self.inputs / "mensajes" / "enlaces.md", "a", encoding="utf-8") as f:
            f.write("| zona_horaria | UTC | repetida |\n")
        with self.assertRaisesRegex(ConfigError, "zona_horaria"):
            textos.cargar(self.inputs)

    def test_falta_un_archivo_de_mensajes(self):
        (self.inputs / "mensajes" / "emoji.md").unlink()
        with self.assertRaisesRegex(ConfigError, "emoji.md"):
            textos.cargar(self.inputs)

    def test_cambiar_un_texto_cambia_el_mensaje_sin_tocar_codigo(self):
        self._editar("Nada por redactar hoy {dia}", "Hoy no hay nada ({dia})")
        mensajes.usar(textos.cargar(self.inputs))
        self.addCleanup(mensajes.usar, None)
        self.assertIn("Hoy no hay nada (30/10)", mensajes.nada_por_redactar("30/10"))


class Cierre(unittest.TestCase):
    R = SimpleNamespace(secuencia="BDB", busquedas=2, nuevas=5, aptas=1, revisar=0, descartadas=4)

    def test_el_resumen_de_captura_enlaza_la_rutina_y_dice_cuando_se_apaga(self):
        cierre = mensajes.fin_captura("03:25")
        texto = mensajes.captura("31/10/2026", "tiempo cumplido", self.R, "completa", [], cierre)
        self.assertIn(mensajes.ajuste("url_rutina"), texto)
        self.assertIn("06:00", texto)
        self.assertIn("se apaga a las 03:25", texto)
        self.assertNotIn("se apaga", mensajes.captura("31/10/2026", "x", self.R, "completa", [], mensajes.fin_captura(None)))

    def test_los_datos_se_escapan_una_sola_vez(self):
        texto = mensajes.aviso_linkedin("linkedin_verificacion", url="https://x/a?b=1&c=<2>")
        self.assertIn("a?b=1&amp;c=&lt;2&gt;", texto)
        self.assertNotIn("&amp;amp;", texto)


class Apagado(unittest.TestCase):
    AHORA = datetime(2026, 10, 31, 3, 0, tzinfo=timezone.utc)

    def test_programa_shutdown_con_el_margen_en_segundos(self):
        llamadas = []
        ejecutar = lambda cmd, **kw: llamadas.append(cmd) or SimpleNamespace(returncode=0)
        hora = apagado.programar(25, self.AHORA, ejecutar, "nt")
        self.assertEqual(llamadas, [["shutdown", "/s", "/t", "1500"]])
        self.assertEqual(hora.minute, 25)

    def test_desactivado_o_fuera_de_windows_no_hace_nada(self):
        def no_debe(*a, **k):
            raise AssertionError("no debe ejecutarse")
        self.assertIsNone(apagado.programar(0, self.AHORA, no_debe, "nt"))
        self.assertIsNone(apagado.programar(25, self.AHORA, no_debe, "posix"))

    def test_si_el_sistema_lo_rechaza_no_se_dice_que_se_apaga(self):
        self.assertIsNone(apagado.programar(25, self.AHORA, lambda *a, **k: SimpleNamespace(returncode=1), "nt"))


if __name__ == "__main__":
    unittest.main()
