"""Prefiltro de detalle (familias del título) y recuento diario de peticiones. Los títulos son reales: de la sonda
del 2026-10-28 y de las 116 ofertas etiquetadas a mano el 2026-10-30."""
import unittest
from dataclasses import replace
from types import SimpleNamespace

from collector.db.connection import transaccion
from collector.filters.titulo import FiltroTitulos
from collector.pipeline import cuota
from collector.pipeline.detail_runner import procesar_detalles
from collector.pipeline import ingest
from collector.pipeline.seleccion import ESPERA_PAIS, seleccionar
from collector.util.reloj import a_iso
from tests.ayudas import CliFalso, config, oferta, sin_pausas
from tests.base import Base

ES = ("Buscamos un analista con experiencia en el área de datos para trabajar con nuestro equipo en la "
      "construcción de informes y la mejora de los procesos de la empresa. Trabajo 100% remoto. Power BI.")


def fila(job_id, titulo, pais="Mexico", motivo=None, fecha="2026-10-20"):
    return {"job_id": job_id, "titulo": titulo, "pais": pais, "motivo_descarte": motivo,
            "fecha_publicacion": fecha, "fecha_hallazgo": "2026-10-28T00:00:00Z"}


class Titulos(unittest.TestCase):
    def setUp(self):
        self.f = FiltroTitulos(config().prefiltro)

    def pasa(self, titulo):
        return self.f.motivo_descarte(titulo) == ""

    def test_titulos_del_perfil_pasan_en_ambos_idiomas_y_con_variantes(self):
        for titulo in ("Analista de datos", "Data Analyst", "Analista de Inteligencia de Negocios", "Científico de datos",
                       "Data Scientist", "Especialista en datos y análitica", "COORDINADOR DE DATOS MAESTROS",
                       "Especialista de IA Aplicada", "Especialista de Medición de Indicadores", "Process Engineer",
                       "Supply Chain Data Analytics Lead", "Power BI Developer / BI Analyst (Temporary)",
                       "Operations Team Leader", "Data Analytics & Strategy Intern"):
            self.assertTrue(self.pasa(titulo), titulo)

    def test_titulos_ajenos_se_descartan_con_la_familia_que_los_aleja(self):
        casos = {"Paid Social Specialist": "marketing", "MARKETING INTELLIGENCE ANALYST": "marketing",
                 "Senior Sales Operations Specialist": "ventas_comercial", "ANALISTA DE CREDITO": "finanzas_contabilidad",
                 "Workforce Planner": "rrhh_atencion", "UX Associate": "fuera_de_perfil", "Ingeniero civil": "sin_familia"}
        for titulo, familia in casos.items():
            self.assertEqual(self.f.motivo_descarte(titulo), f"titulo_fuera_de_perfil:{familia}", titulo)

    def test_las_raices_con_asterisco_cubren_variantes_y_las_exactas_no(self):
        self.assertTrue(self.pasa("Analítica avanzada"))       # analitic*
        self.assertFalse(self.pasa("Bilingual Agent"))          # «bi» es palabra exacta, no prefijo

    def test_cada_familia_suma_una_sola_vez(self):
        self.assertEqual(self.f.puntos("Data Analyst datos data"), 3)

    def test_una_senal_fuerte_compensa_una_palabra_comercial(self):
        self.assertTrue(self.pasa("Commercial Reporting & Sales Operations Assistant"))


class Seleccion(unittest.TestCase):
    def setUp(self):
        self.cfg = config()

    def test_el_pais_de_menor_prioridad_va_ultimo_y_los_puntos_ordenan_dentro_de_cada_pais(self):
        pf = replace(self.cfg.prefiltro, prioridad_pais={**self.cfg.prefiltro.prioridad_pais, "Colombia": 9})
        cfg = SimpleNamespace(**{**vars(self.cfg), "prefiltro": pf})
        filas = [fila("1", "Data Analyst", "Colombia"), fila("2", "Programador SQL", "Mexico"),
                 fila("3", "Analista de datos y BI", "Peru")]
        ids = [e.oferta["job_id"] for e in seleccionar(filas, cfg).elegibles]
        self.assertEqual(ids, ["3", "2", "1"])    # Perú (6 pts), México (3 pts), Colombia al final (prioridad 9)

    def test_a_igualdad_gana_la_mas_reciente(self):
        filas = [fila("vieja", "Data Analyst", fecha="2026-10-01"), fila("nueva", "Data Analyst", fecha="2026-10-20")]
        ids = [e.oferta["job_id"] for e in seleccionar(filas, self.cfg).elegibles]
        self.assertEqual(ids, ["nueva", "vieja"])

    def test_el_orden_lo_fija_la_tabla_de_inputs(self):
        orden = (("recencia", "asc"), ("puntos", "desc"))     # primero la más antigua, sin mirar el país
        cfg = SimpleNamespace(**{**vars(self.cfg), "prefiltro": replace(self.cfg.prefiltro, orden=orden)})
        filas = [fila("nueva", "Data Analyst", "Colombia", fecha="2026-10-20"),
                 fila("vieja", "Data Analyst", "Spain", fecha="2026-10-01")]
        self.assertEqual([e.oferta["job_id"] for e in seleccionar(filas, cfg).elegibles], ["vieja", "nueva"])

    def test_un_pais_sin_prioridad_usa_la_de_por_defecto(self):
        e = seleccionar([fila("1", "Data Analyst", "Atlantis")], self.cfg).elegibles[0]
        self.assertEqual(e.prioridad_pais, self.cfg.prefiltro.prioridad_pais_defecto)

    def test_solo_espera_el_pais_sin_confirmar_y_el_titulo_ajeno_no_es_elegible(self):
        filas = [fila("1", "Head of Finance"), fila("2", "Data Analyst", None, "pais_desconocido"),
                 fila("3", "Data Analyst")]
        s = seleccionar(filas, self.cfg)
        self.assertEqual([e.oferta["job_id"] for e in s.elegibles], ["3"])
        self.assertEqual(s.en_espera, {ESPERA_PAIS: 1})

    def test_limite_recorta_pero_cuenta_todas_las_elegibles(self):
        s = seleccionar([fila(str(i), "Data Analyst") for i in range(5)], self.cfg, 2)
        self.assertEqual((len(s.elegibles), s.total_elegibles), (2, 5))

    def test_la_puntuacion_minima_sale_de_inputs(self):
        cfg = SimpleNamespace(**{**vars(self.cfg), "prefiltro": replace(self.cfg.prefiltro, puntuacion_minima=-99)})
        self.assertEqual(seleccionar([fila("1", "Head of Finance")], cfg).total_elegibles, 1)


class Detalle(Base):
    def test_un_titulo_ajeno_entra_descartado_y_no_gasta_detalle(self):
        self.tanda(CliFalso([[oferta(1, "Head of Finance", "A"), oferta(2, "Data Analyst", "B")]]), 1)
        d = {"description": ES, "employmentType": "Full-time", "isActive": True}
        cli = CliFalso(detalles={"1": d, "2": d})
        procesar_detalles(self.con, self.cfg, cli, sin_pausas(), self.reloj, 5)
        self.assertEqual(cli.llamadas, [("detalle", "2")])
        f = self.con.execute("SELECT estado, motivo_descarte, detalle_obtenido_en FROM ofertas WHERE job_id = '1'").fetchone()
        self.assertEqual(tuple(f), ("descartada", "titulo_fuera_de_perfil:sin_familia", None))

    def test_las_pendientes_de_antes_se_descartan_si_su_titulo_no_pasa(self):
        self.tanda(CliFalso([[oferta(1, "Data Analyst", "A")]]), 1)
        self.con.execute("UPDATE ofertas SET titulo = 'Paid Social Specialist' WHERE job_id = '1'")   # entró con otras reglas
        self.assertEqual(ingest.por_descartar_por_titulo(self.con, self.cfg), 1)
        with transaccion(self.con):
            self.assertEqual(ingest.descartar_por_titulo(self.con, self.cfg), 1)
        self.assertEqual(self.con.execute("SELECT motivo_descarte FROM ofertas WHERE job_id = '1'").fetchone()[0],
                         "titulo_fuera_de_perfil:marketing")


class Cuota(Base):
    def test_un_detalle_con_429_cuenta_como_peticion(self):
        from collector.db import eventos_repo
        with transaccion(self.con):
            eventos_repo.registrar(self.con, "429", a_iso(self.reloj()), "detail 123")
        self.assertEqual(cuota.usadas_hoy(self.con, self.reloj())["detalles"], 1)


if __name__ == "__main__":
    unittest.main()


class ConsultaDeBusqueda(unittest.TestCase):
    def test_la_tanda_pide_el_termino_limpio_con_el_filtro_de_modalidad(self):
        base = Base("setUp")
        base.setUp()
        cli = CliFalso([[oferta(1)]])
        base.tanda(cli, 1)
        self.assertEqual(cli.llamadas[0][1], base.con.execute("SELECT termino FROM combinaciones WHERE ultima_ejecucion IS NOT NULL").fetchone()[0])
        self.assertEqual(cli.llamadas[0][4], config().modalidad.filtro)
        self.assertEqual(config().modalidad.filtro, "2")
        base.con.close()
