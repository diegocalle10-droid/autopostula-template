"""LinkedIn con sesión: lectura de tarjetas y cabeceras, protocolo de sesión, avisos y modalidad por etiqueta. Sin red."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from collector.linkedin import lectura, sesion
from collector.linkedin.errores import LimiteError, LinkedinError, SesionError
from collector.linkedin.sesion_runner import LinkedinSesion
from collector.pipeline.detail_runner import procesar_detalles
from tests.ayudas import DESCRIPCION, CliFalso, config, oferta, sin_pausas
from tests.base import Base

AHORA = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
ETIQUETAS = config().modalidad.etiquetas
CABECERA = """0 notificaciones
Velocity Vehicle Group

Analista de datos

 México  · hace 3 días · Más de 100 solicitudes

Promocionado por técnico de selección · Evaluando solicitudes de forma activa

20K MXN/mes
En remoto
Jornada completa
Solicitud sencilla
Guardar
Usa la IA para evaluar cómo encajarías"""


class Tarjetas(unittest.TestCase):
    def test_tarjeta_remota_con_titulo_repetido_y_fecha(self):
        t = lectura.tarjeta("4484202520", "Analista de datos\nAnalista de datos with verification\nVelocity Vehicle Group\n"
                                          "México (En remoto)\nHace 14 horas\nSolicitud sencilla", ETIQUETAS, AHORA)
        self.assertEqual((t["title"], t["company"], t["location"], t["modalidad"]),
                         ("Analista de datos", "Velocity Vehicle Group", "México", "remoto"))
        self.assertEqual((t["date"], t["url"]), ("2026-10-30", "https://www.linkedin.com/jobs/view/4484202520/"))

    def test_otras_modalidades_y_sin_etiqueta(self):
        base = "A\nA\nDanone\nCiudad de México, México"
        self.assertEqual(lectura.tarjeta("1", base + " (Presencial)", ETIQUETAS, AHORA)["modalidad"], "presencial")
        self.assertEqual(lectura.tarjeta("2", base + " (Híbrido)", ETIQUETAS, AHORA)["modalidad"], "hibrido")
        sin = lectura.tarjeta("3", base + "\nVisto", ETIQUETAS, AHORA)
        self.assertEqual((sin["modalidad"], sin["location"], sin["date"]), (None, "Ciudad de México, México", None))

    def test_un_parentesis_que_no_es_modalidad_se_conserva(self):
        t = lectura.tarjeta("1", "A\nA\nAcme\nGuadalajara (Jalisco)", ETIQUETAS, AHORA)
        self.assertEqual((t["location"], t["modalidad"]), ("Guadalajara (Jalisco)", None))

    def test_tarjeta_sin_pintar(self):
        self.assertIsNone(lectura.tarjeta("1", "  \n ", ETIQUETAS, AHORA))

    def test_fechas_relativas(self):
        casos = {"Hace 14 horas": "2026-10-30", "hace 3 días": "2026-10-28", "Hace 2 semanas": "2026-10-17",
                 "hace 1 mes": "2026-10-01", "2 weeks ago": "2026-10-17", "Evaluando solicitudes": None}
        for texto, esperado in casos.items():
            with self.subTest(texto):
                self.assertEqual(lectura.fecha_relativa(texto, AHORA), esperado)

    def test_url_de_busqueda_con_filtro_de_modalidad_y_solicitud_sencilla(self):
        u = lectura.url_busqueda("analista de datos", "Mexico", "2", 30)
        for trozo in ("f_WT=2", "f_TPR=r2592000", "f_AL=true", "keywords=analista+de+datos"):
            self.assertIn(trozo, u)


class Cabecera(unittest.TestCase):
    def test_oferta_remota(self):
        c = lectura.cabecera(CABECERA, ETIQUETAS)
        self.assertEqual((c["title"], c["company"], c["location"], c["publicada"]),
                         ("Analista de datos", "Velocity Vehicle Group", "México", "hace 3 días"))
        self.assertEqual((c["modalidad"], c["tipo_empleo"], c["solicitud_sencilla"]), ("remoto", "Full-time", True))

    def test_oferta_presencial_sin_solicitud_sencilla(self):
        c = lectura.cabecera(CABECERA.replace("En remoto", "Presencial").replace("Solicitud sencilla\n", ""), ETIQUETAS)
        self.assertEqual((c["modalidad"], c["solicitud_sencilla"]), ("presencial", False))

    def test_pagina_sin_cabecera(self):
        self.assertEqual(lectura.cabecera("nada que ver", ETIQUETAS), {})

    def test_oferta_cerrada(self):
        self.assertTrue(lectura.CERRADA.search("Ya no se aceptan solicitudes para este empleo"))
        self.assertFalse(lectura.CERRADA.search("Evaluando solicitudes de forma activa"))


class PaginaFalsa:
    def __init__(self, destinos):
        self.url, self.destinos, self.visitas = "https://www.linkedin.com/login", list(destinos), []

    def goto(self, url, **_):
        self.visitas.append(url)
        self.url = self.destinos.pop(0) if self.destinos else url

    def wait_for_timeout(self, _):
        pass


class Protocolo(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.perfil, self.avisos = Path(self.dir.name), []
        self.avisar = lambda clave, **datos: self.avisos.append((clave, datos))

    def test_clasificacion_de_lo_que_devuelve_linkedin(self):
        self.assertIsNone(sesion.clasificar("https://www.linkedin.com/jobs/search/", 200, "Resultados"))
        self.assertEqual(sesion.clasificar("https://www.linkedin.com/jobs/", 429, ""), "limite")
        self.assertEqual(sesion.clasificar("https://www.linkedin.com/checkpoint/challenge/x", 200, ""), "limite")
        self.assertEqual(sesion.clasificar("https://www.linkedin.com/jobs/", 200, "Hemos detectado actividad inusual"), "limite")
        oferta_de_fraude = "Analista de fraude. Detectar actividad inusual en transacciones. " + "texto " * 400
        self.assertIsNone(sesion.clasificar("https://www.linkedin.com/jobs/view/1/", 200, oferta_de_fraude))
        self.assertEqual(sesion.clasificar("https://www.linkedin.com/authwall?x", 200, ""), "sesion")
        self.assertEqual(sesion.clasificar("https://www.linkedin.com/login", 200, ""), "sesion")

    def test_la_sesion_valida_se_comprueba_una_vez_al_dia(self):
        p = PaginaFalsa(["https://www.linkedin.com/feed/"])
        self.assertTrue(sesion.protocolo(p, self.perfil, "2026-10-31", self.avisar))
        self.assertEqual(len(p.visitas), 1)
        self.assertTrue(sesion.protocolo(p, self.perfil, "2026-10-31", self.avisar))   # mismo día: no abre nada
        self.assertEqual(len(p.visitas), 1)
        self.assertTrue(sesion.protocolo(PaginaFalsa(["https://www.linkedin.com/feed/"]), self.perfil, "2026-11-01", self.avisar))

    def test_sesion_caducada_avisa_y_espera_el_inicio_de_sesion(self):
        p = PaginaFalsa(["https://www.linkedin.com/login", "https://www.linkedin.com/login"])
        reloj = iter([0, 1, 2, 3, 99999])
        self.assertFalse(sesion.protocolo(p, self.perfil, "2026-10-31", self.avisos.append, espera_s=10, reloj=lambda: next(reloj)))
        self.assertEqual(len(self.avisos), 1)
        self.assertFalse(sesion.validada_hoy(self.perfil, "2026-10-31"))

    def test_una_verificacion_para_sin_esperar_login(self):
        p = PaginaFalsa(["https://www.linkedin.com/checkpoint/challenge/x"])
        self.assertFalse(sesion.protocolo(p, self.perfil, "2026-10-31", self.avisar))
        self.assertEqual(self.avisos[0][0], "linkedin_verificacion")

    def test_dentro(self):
        self.assertTrue(sesion.dentro("https://www.linkedin.com/feed/"))
        self.assertFalse(sesion.dentro("https://www.linkedin.com/login"))
        self.assertFalse(sesion.dentro("https://www.linkedin.com/checkpoint/challenge/abc"))


class PaginaDeAviso:
    def __init__(self, url, texto=""):
        self.url, self._texto = url, texto

    def inner_text(self, *_, **__):
        return self._texto


class Fuente(unittest.TestCase):
    def _fuente(self, url="https://www.linkedin.com/jobs/search/", texto="Resultados"):
        f = LinkedinSesion(".", config())
        f._page = PaginaDeAviso(url, texto)
        return f

    def test_un_aviso_de_linkedin_es_un_limite(self):
        with self.assertRaises(LimiteError):
            self._fuente(texto="Detectamos actividad inusual en tu cuenta")._vigilar()
        with self.assertRaises(LimiteError):
            self._fuente()._vigilar(429)

    def test_pedir_login_otra_vez_es_sesion_caducada(self):
        with self.assertRaises(SesionError):
            self._fuente(url="https://www.linkedin.com/login")._vigilar()

    def test_una_pagina_normal_pasa(self):
        self._fuente()._vigilar(200)

    def test_pedir_la_pagina_2_sin_haber_leido_la_1_falla(self):
        with self.assertRaises(LinkedinError) as e:
            self._fuente()._pasar_pagina(("x", "Mexico", 30, "2", True), 2)
        self.assertEqual(e.exception.codigo, "PAGINA_FUERA_DE_SECUENCIA")


class ModalidadPorEtiqueta(Base):
    def test_tarjeta_de_otra_modalidad_se_descarta_sin_gastar_detalle(self):
        cli = CliFalso([[oferta(1, empresa="A"), dict(oferta(2, empresa="B"), modalidad="presencial"),
                         dict(oferta(3, empresa="C"), modalidad="remoto")]])
        self.tanda(cli, 1)
        estados = {r["job_id"]: (r["estado"], r["motivo_descarte"], r["modalidad"]) for r in
                   self.con.execute("SELECT job_id, estado, motivo_descarte, modalidad FROM ofertas")}
        self.assertEqual(estados["1"], ("pendiente", None, "remoto"))    # sin etiqueta: vale la modalidad de la búsqueda
        self.assertEqual(estados["2"], ("descartada", "modalidad:presencial", "presencial"))
        self.assertEqual(estados["3"], ("pendiente", None, "remoto"))

    def test_el_detalle_con_otra_etiqueta_descarta_y_con_remoto_es_apta(self):
        self.tanda(CliFalso([[oferta(1, empresa="A"), oferta(2, empresa="B")]]), 1)
        detalles = {"1": dict(DESCRIPCION, modalidad="hibrido"), "2": dict(DESCRIPCION, modalidad="remoto")}
        procesar_detalles(self.con, self.cfg, CliFalso(detalles=detalles), sin_pausas(), self.reloj, 5)
        estados = {r["job_id"]: (r["estado"], r["motivo_descarte"], r["modalidad_detectada"]) for r in
                   self.con.execute("SELECT job_id, estado, motivo_descarte, modalidad_detectada FROM ofertas")}
        self.assertEqual(estados["1"], ("descartada", "modalidad:hibrido", "hibrido"))
        self.assertEqual(estados["2"], ("apta", None, "remoto"))
