"""Robustez: bloqueo de concurrencia, respuestas corruptas, fallos seguidos y validación de inputs/."""
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from argparse import Namespace
from datetime import timedelta
from pathlib import Path

from collector.comandos import datos
from collector.config.cargar import cargar_config
from collector.config.modelos import ConfigError
from collector.db import eventos_repo
from collector.db.connection import conectar, transaccion
from collector.db.migrar import migrar
from collector.linkedin.errores import LinkedinError
from collector.pipeline import breaker
from collector.pipeline.detail_runner import procesar_detalles
from collector.util.bloqueo import BloqueoError, bloqueo
from collector.util.reloj import a_iso, de_iso
from tests.ayudas import RAIZ, CliFalso, oferta, sin_pausas
from tests.base import Base


def respuesta(salida="", codigo=0, error=""):
    return subprocess.CompletedProcess(args=[], returncode=codigo, stdout=salida, stderr=error)


class Bloqueo(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.ruta = Path(self.dir.name) / ".lock"

    def test_una_segunda_ejecucion_no_entra_y_al_salir_se_libera(self):
        with bloqueo(self.ruta, 6):
            with self.assertRaises(BloqueoError):
                with bloqueo(self.ruta, 6):
                    pass
        with bloqueo(self.ruta, 6):          # liberado: vuelve a poder tomarse
            pass
        self.assertFalse(self.ruta.exists())

    def test_se_libera_aunque_la_ejecucion_falle(self):
        with self.assertRaises(RuntimeError):
            with bloqueo(self.ruta, 6):
                raise RuntimeError("fallo")
        self.assertFalse(self.ruta.exists())

    def test_un_bloqueo_abandonado_caduca(self):
        self.ruta.write_text("1")
        viejo = time.time() - 7 * 3600
        os.utime(self.ruta, (viejo, viejo))
        with bloqueo(self.ruta, 6):
            self.assertTrue(self.ruta.exists())


class InputsInvalidos(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.inputs = Path(self.dir.name) / "inputs"
        shutil.copytree(RAIZ / "inputs", self.inputs)

    def _editar(self, archivo, viejo, nuevo):
        ruta = self.inputs / archivo
        texto = ruta.read_text(encoding="utf-8")
        self.assertIn(viejo, texto)
        ruta.write_text(texto.replace(viejo, nuevo, 1), encoding="utf-8")

    def test_regex_mal_escrita_falla_al_cargar(self):
        self._editar("idioma.md", "| tecnico | inglés técnico |", "| tecnico | re:(sin cerrar |")
        with self.assertRaisesRegex(ConfigError, "expresión regular inválida"):
            cargar_config(self.inputs)

    def test_modalidad_sin_etiquetas(self):
        self._editar("modalidades.md", "| presencial | 1 | no | presencial, on-site, onsite |", "| presencial | 1 | no |  |")
        with self.assertRaisesRegex(ConfigError, "necesita al menos una etiqueta"):
            cargar_config(self.inputs)

    def test_termino_que_empieza_por_guion(self):
        self._editar("puestos.md", "| 1 | n8n |", "| 1 | -n8n |")
        with self.assertRaisesRegex(ConfigError, "no puede empezar por"):
            cargar_config(self.inputs)

    def test_condicion_desconocida(self):
        self._editar("decisiones.md", "| nivel_dudoso | revisar |", "| nivel_raro | revisar |")
        with self.assertRaisesRegex(ConfigError, "condición desconocida"):
            cargar_config(self.inputs)

    def test_la_ultima_regla_debe_ser_siempre(self):
        self._editar("decisiones.md", "| siempre | apta | |", "| pais_desconocido | apta | |")
        with self.assertRaisesRegex(ConfigError, "«siempre»"):
            cargar_config(self.inputs)

    def test_descartar_exige_motivo(self):
        self._editar("decisiones.md", "| nivel_exigente | descartada | ingles_exigente |", "| nivel_exigente | descartada | |")
        with self.assertRaisesRegex(ConfigError, "necesita motivo"):
            cargar_config(self.inputs)

    def test_la_escalada_necesita_el_primer_escalon(self):
        self._editar("lotes.md", "| 1 | 0 | pausa | 3 |", "| 5 | 0 | pausa | 3 |")
        with self.assertRaisesRegex(ConfigError, "ocurrencias = 1"):
            cargar_config(self.inputs)


class Disyuntor(Base):
    def test_la_parada_por_sospecha_no_caduca_sola(self):
        with transaccion(self.con):
            breaker.parar_por_sospecha(self.con, self.reloj(), "x")
        ok, razon = breaker.puede_ejecutar(self.con, self.cfg, self.reloj() + timedelta(days=3650))
        self.assertFalse(ok)
        self.assertIn("hasta reanudar", razon)

    def test_la_escalada_sale_de_la_tabla(self):
        self.cfg.escalada_429 = tuple(e if e.ocurrencias != 1 else type(e)(1, 0, "pausa", 9) for e in self.cfg.escalada_429)
        with transaccion(self.con):
            breaker.registrar_limite(self.con, self.cfg, self.reloj(), "x")
        pausa = eventos_repo.pausa_activa(self.con, a_iso(self.reloj()))
        self.assertEqual(de_iso(pausa["pausa_hasta"]) - self.reloj(), timedelta(hours=9))


class DetalleRobusto(Base):
    def _con_ofertas(self, n):
        self.tanda(CliFalso([[oferta(i, empresa=f"E{i}") for i in range(1, n + 1)]]), 1)

    def test_una_descripcion_vacia_es_un_fallo_y_no_se_guarda(self):
        self._con_ofertas(1)
        cli = CliFalso(detalles={"1": {"description": "  ", "isActive": True}})
        procesar_detalles(self.con, self.cfg, cli, sin_pausas(), self.reloj, 5)
        fila = self.con.execute("SELECT estado, detalle_obtenido_en FROM ofertas WHERE job_id = '1'").fetchone()
        self.assertEqual(tuple(fila), ("pendiente", None))
        contexto = self.con.execute("SELECT contexto FROM eventos WHERE tipo = 'fallo'").fetchone()[0]
        self.assertIn("DESCRIPCION_VACIA", contexto)

    def test_una_oferta_sin_contenido_dos_veces_se_descarta(self):
        self._con_ofertas(1)
        cli = CliFalso(detalles={"1": {"description": "", "isActive": True}})
        primera = procesar_detalles(self.con, self.cfg, cli, sin_pausas(), self.reloj, 1)
        segunda = procesar_detalles(self.con, self.cfg, cli, sin_pausas(), self.reloj, 1)
        self.assertEqual((primera.ilegibles, segunda.ilegibles), (0, 1))
        fila = self.con.execute("SELECT estado, motivo_descarte FROM ofertas WHERE job_id = '1'").fetchone()
        self.assertEqual(tuple(fila), ("descartada", "detalle_ilegible"))

    def test_un_fallo_de_red_no_descarta_la_oferta(self):
        self._con_ofertas(1)
        cli = CliFalso(detalles={"1": LinkedinError("NAVEGACION", "Target closed")})
        for _ in range(3):
            procesar_detalles(self.con, self.cfg, cli, sin_pausas(), self.reloj, 1)
        self.assertEqual(self.con.execute("SELECT estado FROM ofertas WHERE job_id = '1'").fetchone()[0], "pendiente")

    def test_fallos_seguidos_paran_el_detalle(self):
        self._con_ofertas(5)
        self.cfg.lotes._v["fallos_seguidos_para_parada"] = "2"
        fallo = LinkedinError("INTERNAL_ERROR", "boom")
        cli = CliFalso(detalles={str(i): fallo for i in range(1, 6)})
        r = procesar_detalles(self.con, self.cfg, cli, sin_pausas(), self.reloj, 5)
        self.assertEqual(len([l for l in cli.llamadas if l[0] == "detalle"]), 2)
        self.assertIn("fallos seguidos", r.detenida_por)
        self.assertIsNotNone(eventos_repo.pausa_activa(self.con, a_iso(self.reloj())))


class Reanudar(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)   # el comando deja la conexión abierta
        self.addCleanup(self.dir.cleanup)
        self.db = str(Path(self.dir.name) / "o.sqlite")
        con = conectar(self.db)
        migrar(con)
        ahora = a_iso(de_iso("2099-01-01T00:00:00Z") - timedelta(days=1))
        with transaccion(con):
            eventos_repo.registrar(con, "429", ahora, "x [parada_total]", "2099-12-31T00:00:00Z")
        con.close()

    def test_una_parada_total_exige_forzar(self):
        import collector.util.reloj as reloj
        original = reloj.ahora
        reloj.ahora = lambda: de_iso("2099-01-01T00:00:00Z")
        self.addCleanup(setattr, reloj, "ahora", original)
        self.assertEqual(datos.reanudar(Namespace(db=self.db, forzar=False)), 1)
        self.assertEqual(datos.reanudar(Namespace(db=self.db, forzar=True)), 0)


if __name__ == "__main__":
    unittest.main()
