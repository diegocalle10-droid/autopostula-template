import unittest

from collector.comandos import captura
from collector.db import ofertas_repo
from collector.online import subir
from tests.ayudas import base_en_memoria
from tests.falso_neon import FalsoNeon
from tests.test_db import fila

AHORA = "2026-10-28T12:00:00Z"
# 002/003 de Neon usan sintaxis de PostgreSQL; para las pruebas, la misma tabla en SQLite.
AVISOS_SQLITE = """ALTER TABLE ofertas ADD COLUMN revisada_en TEXT;
CREATE TABLE avisos (aviso_id INTEGER PRIMARY KEY, creado_en TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                     texto TEXT NOT NULL, enviado_en TEXT, tipo TEXT NOT NULL DEFAULT 'texto');"""


class Subida(unittest.TestCase):
    def setUp(self):
        self.local, self.remoto = base_en_memoria(), base_en_memoria()
        self.remoto.execute("DELETE FROM sync_pendientes")
        self.remoto.execute("ALTER TABLE ofertas ADD COLUMN revisada_en TEXT")   # como 003_mensajes.sql en Neon
        self.addCleanup(self.local.close)
        self.addCleanup(self.remoto.close)
        for i in range(1, 6):
            ofertas_repo.insertar_nueva(self.local, fila(str(i)), AHORA)
        self.local.execute("INSERT INTO oferta_keywords VALUES ('1', 'python')")
        self.local.commit()

    def n(self, con, tabla="ofertas"):
        return con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]

    def test_sube_todo_y_vacia_la_cola(self):
        subir.subir_pendientes(self.local, FalsoNeon(self.remoto), log=lambda m: None)
        self.assertEqual((self.n(self.remoto), self.n(self.remoto, "oferta_keywords")), (5, 1))
        self.assertEqual(self.n(self.local, "sync_pendientes"), 0)

    def test_repetir_no_duplica_y_propaga_cambios(self):
        subir.subir_pendientes(self.local, FalsoNeon(self.remoto), log=lambda m: None)
        self.local.execute("UPDATE ofertas SET estado = 'apta' WHERE job_id = '2'")
        self.local.commit()
        self.assertEqual(subir.total_pendientes(self.local), {"ofertas": 1})
        subir.subir_pendientes(self.local, FalsoNeon(self.remoto), log=lambda m: None)
        self.assertEqual(self.n(self.remoto), 5)
        self.assertEqual(self.remoto.execute("SELECT estado FROM ofertas WHERE job_id = '2'").fetchone()[0], "apta")

    def test_borrado_local_se_borra_en_neon(self):
        subir.subir_pendientes(self.local, FalsoNeon(self.remoto), log=lambda m: None)
        self.local.execute("DELETE FROM ofertas WHERE job_id = '3'")
        self.local.commit()
        subir.subir_pendientes(self.local, FalsoNeon(self.remoto), log=lambda m: None)
        self.assertEqual(self.n(self.remoto), 4)

    def test_duplicadas_suben_despues_de_su_original(self):
        self.local.execute("UPDATE ofertas SET duplicada_de = '5' WHERE job_id = '1'")
        self.local.commit()
        subir.subir_pendientes(self.local, FalsoNeon(self.remoto), log=lambda m: None)
        self.assertEqual(self.remoto.execute("SELECT duplicada_de FROM ofertas WHERE job_id = '1'").fetchone()[0], "5")

    def test_reintenta_y_retoma_sin_repetir(self):
        subir.LOTE["ofertas"] = 2
        self.addCleanup(subir.LOTE.pop, "ofertas")
        intentos = []

        def abrir():
            intentos.append(1)
            return FalsoNeon(self.remoto, falla_en=4 if len(intentos) == 1 else None)   # corta tras el primer lote
        ok = subir.con_reintentos(self.local, abrir, log=lambda m: None, espera=lambda s: None)
        self.assertTrue(ok)
        self.assertEqual(len(intentos), 2)
        self.assertEqual(self.n(self.remoto), 5)
        self.assertEqual(self.n(self.local, "sync_pendientes"), 0)

    def test_si_fallan_los_tres_la_cola_se_conserva(self):
        ok = subir.con_reintentos(self.local, lambda: FalsoNeon(self.remoto, falla_en=1), log=lambda m: None,
                                  espera=lambda s: None)
        self.assertFalse(ok)
        self.assertEqual(self.n(self.remoto), 0)
        self.assertEqual(subir.total_pendientes(self.local)["ofertas"], 5)


class Horas(unittest.TestCase):
    def test_no_pregunta_con_horas_ni_sin_terminal(self):
        self.assertEqual(captura.preguntar_horas(3, 5, interactivo=True), 3)
        self.assertEqual(captura.preguntar_horas(0, 5, interactivo=False), 5)

    def test_pregunta_y_acepta_coma_y_vacio(self):
        self.assertEqual(captura.preguntar_horas(0, 5, entrada=lambda _: "1,5", interactivo=True), 1.5)
        self.assertEqual(captura.preguntar_horas(0, 5, entrada=lambda _: "", interactivo=True), 5)
        respuestas = iter(["abc", "2"])
        self.assertEqual(captura.preguntar_horas(0, 5, entrada=lambda _: next(respuestas), interactivo=True), 2.0)


if __name__ == "__main__":
    unittest.main()


class Pdfs(unittest.TestCase):
    def setUp(self):
        import sqlite3
        import tempfile
        from pathlib import Path
        from collector.online import esquema
        from tests.ayudas import RAIZ, config
        self.cfg, self.raiz, self.tmp = config(), RAIZ, Path(tempfile.mkdtemp())
        self.remoto = sqlite3.connect(":memory:")
        self.remoto.executescript((esquema.CARPETA / "001_neon.sql").read_text(encoding="utf-8"))
        self.remoto.executescript(AVISOS_SQLITE)
        self.addCleanup(self.remoto.close)
        self.remoto.execute("INSERT INTO ofertas (job_id,url,titulo,empresa,fecha_hallazgo,ultima_vista,modalidad,estado) "
                            "VALUES ('1','u','Analista','Acme','x','x','remoto','apta')")
        base = (RAIZ / "CV/base/data_analytics.md").read_text(encoding="utf-8")
        self.valido = self.sin_raya_en_logros(base)

    @staticmethod
    def sin_raya_en_logros(base):
        """El CV base lleva rayas largas en los logros (el estilo las prohíbe) y en datos (se dejan)."""
        salida, en_cargo = [], False
        for l in base.splitlines():
            en_cargo = l.startswith("### ") or (en_cargo and not l.startswith("## "))
            salida.append(l.replace("—", ",") if en_cargo and l.startswith("- ") else l)
        return "\n".join(salida)

    def registrar(self, md):
        self.remoto.execute("INSERT INTO emparejamientos (job_id,estado,cv_id,afinidad,cv_md,emparejado_en) "
                            "VALUES ('1','redactada','data_analytics',80,?,'t')", (md,))

    def pasada(self, enviar=None):
        from collector.online import pdfs
        return pdfs.procesar(FalsoNeon(self.remoto), self.cfg, self.raiz, self.tmp, AHORA, log=lambda m: None,
                             enviar=enviar)

    def estado(self):
        return self.remoto.execute("SELECT estado, intentos, rechazo FROM emparejamientos").fetchone()

    def test_cv_valido_se_valida_y_genera_pdf(self):
        self.registrar(self.valido)
        self.assertEqual(self.pasada()["validadas"], ["1"])
        self.assertEqual(self.estado()[:2], ("validada", 0))
        self.assertTrue((self.tmp / "1_acme" / "CV - Analista.pdf").is_file())

    def test_avisa_con_el_pdf_y_el_enlace_y_no_repite(self):
        self.registrar(self.valido)
        enviados = []
        self.assertEqual(self.pasada(lambda pdf, texto: enviados.append((pdf.is_file(), texto)))["avisadas"], ["1"])
        self.assertEqual(enviados[0][0], True)
        self.assertIn("Acme", enviados[0][1])
        self.assertIn("afinidad 80 %", enviados[0][1])
        self.assertIsNotNone(self.remoto.execute("SELECT notificado_en FROM emparejamientos").fetchone()[0])
        self.assertEqual(self.pasada(lambda *a: enviados.append(a))["avisadas"], [])
        self.assertEqual(len(enviados), 1)

    def test_si_el_aviso_falla_se_reintenta_en_la_siguiente_pasada(self):
        self.registrar(self.valido)

        def roto(pdf, texto):
            raise RuntimeError("sin red")
        self.assertEqual(self.pasada(roto)["avisadas"], [])
        self.assertEqual(self.estado()[0], "validada")
        self.assertEqual(self.pasada(lambda pdf, texto: None)["avisadas"], ["1"])

    def test_cv_con_marca_se_rechaza_y_cuenta_el_intento(self):
        self.registrar(self.valido + "\nTODO completar\n")
        self.assertEqual(self.pasada()["rechazadas"], ["1"])
        estado, intentos, rechazo = self.estado()
        self.assertEqual((estado, intentos), ("rechazada", 1))
        self.assertIn("plantilla", rechazo)
        self.assertEqual(self.remoto.execute("SELECT COUNT(*) FROM ofertas_por_redactar").fetchone()[0], 1)

    def test_tras_tres_rechazos_sale_de_la_vista(self):
        self.registrar("vacío")
        self.remoto.execute("UPDATE emparejamientos SET estado = 'rechazada', intentos = 3")
        self.assertEqual(self.remoto.execute("SELECT COUNT(*) FROM ofertas_por_redactar").fetchone()[0], 0)

    def test_oferta_apta_sin_emparejamiento_esta_por_redactar(self):
        self.assertEqual(self.remoto.execute("SELECT COUNT(*) FROM ofertas_por_redactar").fetchone()[0], 1)


class Avisos(unittest.TestCase):
    def setUp(self):
        import sqlite3
        self.remoto = sqlite3.connect(":memory:")
        self.remoto.execute("CREATE TABLE ofertas (job_id TEXT)")
        self.remoto.executescript(AVISOS_SQLITE)
        self.remoto.executemany("INSERT INTO avisos (texto) VALUES (?)", [("uno",), ("dos",)])
        self.addCleanup(self.remoto.close)

    def test_envia_en_orden_y_no_repite(self):
        from collector.online import avisos
        enviados = []
        self.assertEqual(avisos.enviar_pendientes(FalsoNeon(self.remoto), enviados.append, AHORA, log=lambda m: None), 2)
        self.assertEqual(enviados, ["uno", "dos"])
        self.assertEqual(avisos.enviar_pendientes(FalsoNeon(self.remoto), enviados.append, AHORA, log=lambda m: None), 0)

    def test_si_falla_se_para_y_conserva_el_resto(self):
        from collector.online import avisos

        def roto(texto):
            raise RuntimeError("sin red")
        self.assertEqual(avisos.enviar_pendientes(FalsoNeon(self.remoto), roto, AHORA, log=lambda m: None), 0)
        self.assertEqual(self.remoto.execute("SELECT COUNT(*) FROM avisos WHERE enviado_en IS NULL").fetchone()[0], 2)
