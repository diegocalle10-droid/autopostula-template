"""Mensajes de Telegram: plantillas, avisos de rechazo y sin CV, resumen de la rutina, alertas de la captura,
y las dos garantías de Neon (las ofertas existentes no se tocan; lo revisado a mano no se pisa)."""
import sqlite3
import unittest
from types import SimpleNamespace

from collector.comandos import captura
from collector.online import mensajes, pdfs, rutina, subir
from collector.online.esquema import CARPETA
from tests.ayudas import CliFalso, base_en_memoria, oferta
from tests.base import Base
from tests.falso_neon import FalsoNeon
from tests.test_db import fila
from tests.test_online import AHORA, AVISOS_SQLITE

O = {"job_id": "4012345678", "empresa": "Acme <SL>", "titulo": "Analista BI", "url": "https://x/4012345678",
     "ubicacion": "Madrid", "modalidad": "híbrido", "cv_id": "data_analytics", "afinidad": 72, "motivo": "falta SAP"}


def neon():
    con = sqlite3.connect(":memory:")
    con.executescript((CARPETA / "001_neon.sql").read_text(encoding="utf-8"))
    con.executescript(AVISOS_SQLITE)
    con.execute("INSERT INTO ofertas (job_id,url,titulo,empresa,fecha_hallazgo,ultima_vista,modalidad,estado) "
                "VALUES ('1','https://x/1','Analista','Acme','x','x','remoto','apta')")
    return con


def avisos(con, tipo=None):
    sql = "SELECT texto FROM avisos" + (" WHERE tipo = ?" if tipo else "") + " ORDER BY aviso_id"
    return [t for (t,) in con.execute(sql, (tipo,) if tipo else ())]


class Plantillas(unittest.TestCase):
    def test_todas_llevan_el_id_en_su_linea_y_escapan_el_html(self):
        for texto in (mensajes.cv_listo(O), mensajes.sin_cv(O), mensajes.rechazo(O, 1, "ocupa 3 páginas")):
            self.assertIn("\nID: 4012345678\n", texto)
            self.assertIn("Acme &lt;SL&gt;", texto)

    def test_el_pie_del_pdf_cabe_en_telegram(self):
        largo = dict(O, empresa="E" * 2000, titulo="T" * 2000, url="u" * 2000)
        self.assertLessEqual(len(mensajes.cv_listo(largo)), 1024)

    def test_las_listas_largas_se_resumen_sin_pasar_de_4096(self):
        quedan = [dict(O, job_id=str(i), titulo="T" * 150) for i in range(200)]
        texto = mensajes.resumen_rutina("30/10/2026", 5, 1, 2, quedan)
        self.assertLess(len(texto), 4096)
        self.assertIn("más", texto.splitlines()[-1])

    def test_el_rechazo_final_lleva_consulta_y_enlace_a_neon(self):
        texto = mensajes.rechazo(O, 3, "x")
        self.assertIn("<code>SELECT * FROM emparejamientos WHERE job_id = '4012345678';</code>", texto)
        self.assertIn(mensajes.ajuste("url_consola_neon"), texto)
        self.assertIn("No se reintenta más", texto)


class Rechazos(unittest.TestCase):
    def test_avisa_solo_en_el_primero_y_el_tercero(self):
        from tests.ayudas import config, RAIZ
        con = neon()
        self.addCleanup(con.close)
        con.execute("INSERT INTO emparejamientos (job_id,estado,cv_id,afinidad,cv_md,emparejado_en) "
                    "VALUES ('1','redactada','data_analytics',80,'TODO','t')")
        for _ in range(3):
            pdfs.procesar(FalsoNeon(con), config(), RAIZ, RAIZ / "no-se-usa", AHORA, log=lambda m: None)
            con.execute("UPDATE emparejamientos SET estado = 'redactada'")   # la rutina lo reescribe
        textos = avisos(con, "rechazo")
        self.assertEqual(len(textos), 2)
        self.assertIn("intento 1 de 3", textos[0])
        self.assertIn("intento 3 de 3", textos[1])


class Rutina(unittest.TestCase):
    def setUp(self):
        self.con = neon()
        self.addCleanup(self.con.close)

    def test_un_aviso_por_cada_sin_cv_y_una_sola_vez(self):
        self.con.execute("INSERT INTO emparejamientos (job_id,estado,afinidad,motivo,emparejado_en) "
                         "VALUES ('1','sin_cv',20,'falta SAP','2999')")
        self.assertEqual(rutina.encolar_sin_cv(FalsoNeon(self.con), AHORA), 1)
        self.assertEqual(rutina.encolar_sin_cv(FalsoNeon(self.con), AHORA), 0)
        self.assertIn("ID: 1", avisos(self.con, "sin_cv")[0])

    def test_nada_por_redactar(self):
        self.con.execute("UPDATE ofertas SET estado = 'descartada', motivo_descarte = 'x'")
        self.assertEqual(rutina.encolar_resumen(FalsoNeon(self.con), "30/10/2026"), "nada")
        self.assertEqual(avisos(self.con), ["ℹ️ Nada por redactar hoy 30/10/2026"])

    def test_rutina_que_no_registra_nada_avisa_de_lo_que_queda(self):
        self.assertEqual(rutina.encolar_resumen(FalsoNeon(self.con), "30/10/2026"), "sin_registros")
        self.assertIn("• 1 · Acme", avisos(self.con)[0])

    def test_resumen_cuenta_solo_lo_de_esta_ejecucion(self):
        self.con.execute("INSERT INTO emparejamientos (job_id,estado,cv_id,afinidad,cv_md,emparejado_en) "
                         "VALUES ('1','redactada','data_analytics',80,'x','2999-01-01T00:00:00Z')")
        self.assertEqual(rutina.encolar_resumen(FalsoNeon(self.con), "30/10/2026"), "resumen")
        self.assertIn("Redactados 1", avisos(self.con)[0])
        self.con.execute("UPDATE emparejamientos SET emparejado_en = '2000-01-01T00:00:00Z'")   # ya contado
        self.con.execute("UPDATE ofertas SET estado = 'descartada', motivo_descarte = 'x'")
        self.assertEqual(rutina.encolar_resumen(FalsoNeon(self.con), "31/10/2026"), "nada")


class Neon(unittest.TestCase):
    def test_lo_revisado_a_mano_en_neon_no_se_pisa(self):
        local, remoto = base_en_memoria(), base_en_memoria()
        self.addCleanup(local.close)
        self.addCleanup(remoto.close)
        remoto.execute("DELETE FROM sync_pendientes")
        remoto.execute("ALTER TABLE ofertas ADD COLUMN revisada_en TEXT")
        from collector.db import ofertas_repo
        ofertas_repo.insertar_nueva(local, fila("1", estado="revisar", motivo_descarte="ingles_dudoso"), AHORA)
        subir.subir_pendientes(local, FalsoNeon(remoto), log=lambda m: None)
        remoto.execute("UPDATE ofertas SET estado = 'apta', revisada_en = '2026-10-30' WHERE job_id = '1'")
        local.execute("UPDATE ofertas SET titulo = 'cambio local' WHERE job_id = '1'")
        subir.subir_pendientes(local, FalsoNeon(remoto), log=lambda m: None)
        self.assertEqual(remoto.execute("SELECT estado FROM ofertas WHERE job_id = '1'").fetchone()[0], "apta")


class OfertaExistente(Base):
    def test_si_vuelve_a_salir_no_se_toca_ni_se_vuelve_a_subir(self):
        self.tanda(CliFalso([[oferta(1)]]), 1)
        antes = self.con.execute("SELECT * FROM ofertas WHERE job_id = '1'").fetchone()
        self.con.execute("DELETE FROM sync_pendientes")
        self.con.execute("UPDATE combinaciones SET proxima_ejecucion = '2000-01-01T00:00:00Z'")
        self.tanda(CliFalso([[oferta(1)]]), 1)
        self.assertEqual(tuple(self.con.execute("SELECT * FROM ofertas WHERE job_id = '1'").fetchone()), tuple(antes))
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM sync_pendientes WHERE tabla = 'ofertas'").fetchone()[0], 0)


class AlertasCaptura(unittest.TestCase):
    def setUp(self):
        self.con = base_en_memoria()
        self.addCleanup(self.con.close)

    def r(self, motivo, limite=False):
        return SimpleNamespace(motivo=motivo, limite=limite)

    def test_finales_normales_no_alertan(self):
        for motivo in captura.FINALES_NORMALES:
            self.assertIsNone(captura.anomalia(self.con, self.r(motivo), AHORA))

    def test_429_y_parada_total(self):
        self.assertEqual(captura.anomalia(self.con, self.r("429", limite=True), AHORA)[0], "límite de LinkedIn (429)")
        self.con.execute("INSERT INTO eventos (ocurrido_en, tipo, contexto, pausa_hasta) "
                         "VALUES (?, '429', 'x [parada_total]', '2999-01-01T00:00:00Z')", (AHORA,))
        titulo, datos = captura.anomalia(self.con, self.r("429", limite=True), AHORA)
        self.assertEqual(titulo, "parada total")
        self.assertTrue(any(d.startswith("Pausa hasta") for d in datos))

    def test_otra_parada_es_anomala(self):
        self.assertEqual(captura.anomalia(self.con, self.r("fallos seguidos en el detalle"), AHORA)[0],
                         "detenida antes de tiempo")


if __name__ == "__main__":
    unittest.main()


class TandaDeDetalles(unittest.TestCase):
    def test_el_resumen_agrupa_lo_que_hay_por_revisar_por_motivo(self):
        r = SimpleNamespace(procesadas=5, aptas=1, revisar=3, descartadas=1, detenida_por=None)
        revisar = [dict(O, job_id=str(i), motivo_descarte="ingles_dudoso") for i in range(3)]
        texto = mensajes.tanda_detalles("31/10/2026", r, "completa", revisar)
        self.assertIn("Evaluadas 5 (aptas 1, revisar 3, descartadas 1)", texto)
        self.assertIn("3 ofertas por revisar (ingles_dudoso 3)", texto)
        self.assertIn(mensajes.ajuste("url_consola_neon"), texto)

    def test_sin_nada_por_revisar_no_hay_bloque_y_si_se_paro_se_dice(self):
        r = SimpleNamespace(procesadas=0, aptas=0, revisar=0, descartadas=0, detenida_por="429")
        texto = mensajes.tanda_detalles("31/10/2026", r, "sin cambios", [])
        self.assertIn("Detenida: 429", texto)
        self.assertNotIn("por revisar", texto)
