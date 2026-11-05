import unittest
from dataclasses import replace
from datetime import timedelta

from collector.config.modelos import ReglaIngreso
from collector.db import combinaciones_repo, eventos_repo, ofertas_repo
from collector.db.connection import transaccion
from collector.linkedin.errores import LimiteError, LinkedinError
from collector.pipeline import breaker
from collector.pipeline.batch_runner import ejecutar_tanda, jobage_para
from collector.pipeline.detail_runner import procesar_detalles
from collector.util.reloj import a_iso, de_iso
from tests.ayudas import CliFalso, oferta, reloj_fijo, sin_pausas, obtener_combinacion
from tests.base import Base

ES = ("Buscamos un analista con experiencia en el área de datos para trabajar con nuestro equipo en la "
      "construcción de informes y la mejora de los procesos de la empresa. Trabajo 100% remoto. Power BI.")


class Agenda(Base):
    def test_agenda_completa(self):
        n = len(self.cfg.terminos) * len(self.cfg.ubicaciones)   # cada término en cada ubicación
        self.assertEqual(combinaciones_repo.contar(self.con), {"total": n, "activas": n})

    def test_orden_por_prioridad(self):
        prios = [c["prioridad"] for c in combinaciones_repo.debidas(self.con, a_iso(self.reloj()), 40)]
        self.assertEqual(prios, sorted(prios))
        self.assertEqual(prios[0], 1)


class Tanda(Base):
    def test_una_tanda_guarda_y_programa_la_siguiente(self):
        cli = CliFalso([[oferta(1), oferta(2)], [oferta(3)], []])
        r = self.tanda(cli, 3)
        self.assertEqual((r.consultas, r.nuevas, r.combinaciones), (3, 3, 3))
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM ofertas").fetchone()[0], 3)
        c = obtener_combinacion(self.con, 1)
        self.assertEqual(de_iso(c["proxima_ejecucion"]) - de_iso(c["ultima_ejecucion"]), timedelta(days=10))
        self.assertEqual(obtener_combinacion(self.con, 3)["pasadas_sin_nuevas"], 1)   # la vacía

    def test_una_segunda_tanda_no_repite_combinaciones(self):
        self.tanda(CliFalso([[oferta(1)]] * 2), 2)
        cli2 = CliFalso([[oferta(1)]] * 2)
        self.tanda(cli2, 2)
        pares = [(l[1], l[2]) for l in cli2.llamadas]
        self.assertEqual(len(set(pares)), 2)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM ofertas").fetchone()[0], 1)   # misma oferta, sin duplicar

    def test_misma_oferta_por_varias_consultas_suma_hallazgos(self):
        self.tanda(CliFalso([[oferta(1)], [oferta(1)]]), 2)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM hallazgos WHERE job_id = '1'").fetchone()[0], 2)

    def test_pagina_siguiente_solo_si_la_actual_trae_nuevas(self):
        pagina_llena = [oferta(i) for i in range(100, 125)]
        cli = CliFalso([pagina_llena, [oferta(200)]])
        r = self.tanda(cli, 5)
        self.assertEqual([l[5] for l in cli.llamadas[:2]], [1, 2])    # pidió página 1 y 2
        self.assertEqual(r.nuevas, 26)

    def test_pagina_llena_de_titulos_fuera_de_perfil_no_pide_otra(self):
        relleno = [oferta(i, titulo="Paid Social Specialist") for i in range(300, 325)]
        cli = CliFalso([relleno, [oferta(400)]])
        self.tanda(cli, 5)
        self.assertEqual([l[5] for l in cli.llamadas[:2]], [1, 1])      # nuevas todas, pero ninguna del perfil: no hay página 2

    def test_pagina_con_la_mitad_de_titulos_de_perfil_si_pide_otra(self):
        mixta = [oferta(i) for i in range(500, 510)] + [oferta(i, titulo="Paid Social Specialist") for i in range(510, 525)]
        cli2 = CliFalso([mixta, [oferta(600)]])
        self.tanda(cli2, 2)
        self.assertEqual([l[5] for l in cli2.llamadas[:2]], [1, 2])    # justo la mitad del perfil: sigue

    def test_pagina_llena_pero_ya_conocida_no_pide_otra(self):
        pagina = [oferta(i) for i in range(100, 125)]
        self.tanda(CliFalso([pagina, []]), 2)
        con_conocidas = CliFalso([pagina])
        # misma página en otra combinación: todo conocido (0 nuevas) -> no pide la 2.ª página
        self.con.execute("UPDATE combinaciones SET proxima_ejecucion = '2000-01-01T00:00:00Z'")
        self.tanda(con_conocidas, 1)
        self.assertEqual(len(con_conocidas.llamadas), 1)

    def test_region_descarta_pais_no_hispano(self):
        reg = self.cfg.ubicaciones[-1]            # una región (Latin America)
        self.assertEqual(reg.tipo, "region")
        self.con.execute("UPDATE combinaciones SET proxima_ejecucion = '2999-01-01T00:00:00Z'")
        self.con.execute("UPDATE combinaciones SET proxima_ejecucion = '2000-01-01T00:00:00Z' WHERE ubicacion_frase = ?", (reg.frase,))
        self.tanda(CliFalso([[oferta(1, ubicacion="Sao Paulo, Brazil", empresa="A"),
                              oferta(2, ubicacion="Bogota, Colombia", empresa="B"),
                              oferta(3, ubicacion="Greater Madrid Metropolitan Area", empresa="C")]]), 1)
        estados = {r["job_id"]: (r["estado"], r["motivo_descarte"]) for r in self.con.execute("SELECT * FROM ofertas")}
        self.assertEqual(estados["1"], ("descartada", "pais_excluido:Brazil"))
        self.assertEqual(estados["2"], ("pendiente", None))
        self.assertEqual(estados["3"], ("pendiente", "pais_desconocido"))   # no se descarta: se evaluará y irá a revisar

    def _oferta_de_pais_desconocido(self):
        self.con.execute("UPDATE combinaciones SET proxima_ejecucion = '2999-01-01T00:00:00Z'")
        reg = self.cfg.ubicaciones[-1]
        self.con.execute("UPDATE combinaciones SET proxima_ejecucion = '2000-01-01T00:00:00Z' WHERE ubicacion_frase = ?", (reg.frase,))
        self.tanda(CliFalso([[oferta(3, ubicacion="Greater Madrid Metropolitan Area")]]), 1)
        return {"3": {"description": ES, "employmentType": "Full-time", "isActive": True}}

    def test_pais_desconocido_espera_sin_pedir_detalle(self):
        cli = CliFalso(detalles=self._oferta_de_pais_desconocido())
        procesar_detalles(self.con, self.cfg, cli, sin_pausas(), self.reloj, 5)
        self.assertEqual(cli.llamadas, [])
        o = self.con.execute("SELECT estado, motivo_descarte FROM ofertas WHERE job_id = '3'").fetchone()
        self.assertEqual(tuple(o), ("pendiente", "pais_desconocido"))   # no se descarta: espera

    def test_pais_desconocido_acaba_en_revisar_si_la_regla_pide_detalle(self):
        ingreso = {**self.cfg.decisiones.ingreso, "pais_desconocido": ReglaIngreso("evaluar", "pais_desconocido")}
        self.cfg.decisiones = replace(self.cfg.decisiones, ingreso=ingreso)
        procesar_detalles(self.con, self.cfg, CliFalso(detalles=self._oferta_de_pais_desconocido()),
                          sin_pausas(), self.reloj, 5)
        o = self.con.execute("SELECT estado, motivo_descarte, idioma_contenido FROM ofertas WHERE job_id = '3'").fetchone()
        self.assertEqual(tuple(o), ("revisar", "pais_desconocido", "es"))

    def test_republicacion_con_id_nuevo_se_marca_duplicada(self):
        self.tanda(CliFalso([[oferta(1), oferta(2)]]), 1)    # mismos empresa+título+ubicación, distinto id
        o = {r["job_id"]: (r["estado"], r["motivo_descarte"]) for r in self.con.execute("SELECT * FROM ofertas")}
        self.assertEqual(o["1"][0], "pendiente")
        self.assertEqual(o["2"], ("descartada", "duplicada_de:1"))

    def test_de_madrugada_tambien_busca(self):
        cli = CliFalso([[oferta(1)]])
        ejecutar_tanda(self.con, self.cfg, cli, sin_pausas(), reloj_fijo(dia=29, hora=3), 1)
        self.assertTrue(cli.llamadas)   # sin horario fijo: la captura corre cuando el usuario la lanza

    def test_jobage_primer_barrido_y_mantenimiento(self):
        c = obtener_combinacion(self.con, 1)
        self.assertEqual(jobage_para(c, self.cfg, self.reloj()), 30)
        self.con.execute("UPDATE combinaciones SET ultima_ejecucion = ? WHERE combinacion_id = 1",
                         (a_iso(self.reloj() - timedelta(days=9, hours=2)),))
        c = obtener_combinacion(self.con, 1)
        self.assertEqual(jobage_para(c, self.cfg, self.reloj()), 11)   # 10 días redondeados + 1 de margen


class Disyuntor(Base):
    def test_429_para_la_tanda_y_deja_pausa_de_3_horas(self):
        r = self.tanda(CliFalso([[oferta(1)], LimiteError("SEARCH_FAILED", "Request failed: 429")]), 5)
        self.assertEqual(r.consultas, 1)
        self.assertIn("429", r.detenida_por)
        p = eventos_repo.pausa_activa(self.con, a_iso(self.reloj()))
        self.assertEqual(de_iso(p["pausa_hasta"]) - self.reloj(), timedelta(hours=3))

    def test_con_pausa_activa_no_se_hace_ninguna_peticion(self):
        self.tanda(CliFalso([LimiteError("SEARCH_FAILED", "Request failed: 429")]), 5)
        cli = CliFalso([[oferta(9)]])
        r = self.tanda(cli, 5)
        self.assertEqual(cli.llamadas, [])
        self.assertIn("pausa activa", r.detenida_por)

    def test_escalada_primero_3h_luego_hasta_manana_luego_parada_total(self):
        ahora = self.reloj()
        notas = []
        for _ in range(3):
            with transaccion(self.con):
                notas.append(breaker.registrar_limite(self.con, self.cfg, ahora, "x"))
        self.assertEqual(notas, ["pausa", "hasta_manana", "parada_total"])

    def test_la_combinacion_con_429_no_se_da_por_hecha(self):
        self.tanda(CliFalso([LimiteError("SEARCH_FAILED", "Request failed: 429")]), 1)
        self.assertIsNone(obtener_combinacion(self.con, 1)["ultima_ejecucion"])

    def test_reanudar_levanta_la_pausa(self):
        self.tanda(CliFalso([LimiteError("SEARCH_FAILED", "Request failed: 429")]), 1)
        with transaccion(self.con):
            self.assertEqual(eventos_repo.cancelar_pausas(self.con, a_iso(self.reloj())), 1)
        self.assertIsNone(eventos_repo.pausa_activa(self.con, a_iso(self.reloj())))

    def test_fallo_no_429_reprograma_y_sigue(self):
        cli = CliFalso([LinkedinError("SEARCH_FAILED", "Request failed: 500"), [oferta(1)]])
        r = self.tanda(cli, 2)
        self.assertEqual(r.consultas, 2)
        c = obtener_combinacion(self.con, 1)
        self.assertIsNone(c["ultima_ejecucion"])
        self.assertEqual(de_iso(c["proxima_ejecucion"]) - self.reloj(), timedelta(hours=1))

    def test_lista_sin_tarjetas_dos_veces_salta_a_la_siguiente_sin_pausar(self):
        sin = LinkedinError("LISTA_SIN_TARJETAS", "la página no trae lista")
        cli = CliFalso([sin, sin, [oferta(1)], [oferta(2)]])
        r = self.tanda(cli, 4)
        self.assertEqual(r.consultas, 4)
        self.assertNotIn("disyuntor", r.detenida_por or "")
        self.assertIsNone(eventos_repo.pausa_activa(self.con, a_iso(self.reloj())))
        self.assertIsNone(obtener_combinacion(self.con, 1)["ultima_ejecucion"])
        self.assertIsNotNone(obtener_combinacion(self.con, 2)["ultima_ejecucion"])


class Detalle(Base):
    def _preparar(self, detalles):
        self.tanda(CliFalso([[oferta(1), oferta(2, titulo="Data Analyst", empresa="Otra")]]), 1)
        cli = CliFalso(detalles=detalles)
        return cli, procesar_detalles(self.con, self.cfg, cli, sin_pausas(), self.reloj, 10)

    def test_evalua_y_guarda_keywords(self):
        d = {"description": ES, "employmentType": "Full-time", "isActive": True}
        _, r = self._preparar({"1": d, "2": d})
        self.assertEqual((r.procesadas, r.aptas), (2, 2))
        o = self.con.execute("SELECT * FROM ofertas WHERE job_id = '1'").fetchone()
        self.assertEqual((o["estado"], o["activa"], o["tipo_empleo"], o["idioma_contenido"]), ("apta", 1, "Full-time", "es"))
        kws = [k["keyword"] for k in self.con.execute("SELECT keyword FROM oferta_keywords WHERE job_id = '1'")]
        self.assertIn("power bi", kws)

    def test_oferta_cerrada_en_404_se_guarda_como_descartada(self):
        _, r = self._preparar({"1": {"description": ES, "isActive": True}})   # la 2 -> NOT_FOUND
        self.assertEqual(r.descartadas, 1)
        o = self.con.execute("SELECT estado, motivo_descarte FROM ofertas WHERE job_id = '2'").fetchone()
        self.assertEqual(tuple(o), ("descartada", "cerrada"))
        self.assertEqual(ofertas_repo.pendientes_de_detalle(self.con), [])      # no se vuelve a pedir

    def test_429_en_detalle_para_y_pausa(self):
        self.tanda(CliFalso([[oferta(1)]]), 1)
        cli = CliFalso(detalles={"1": LimiteError("DETAIL_FAILED", "Request failed: 429")})
        r = procesar_detalles(self.con, self.cfg, cli, sin_pausas(), self.reloj, 5)
        self.assertIn("429", r.detenida_por)
        self.assertIsNotNone(eventos_repo.pausa_activa(self.con, a_iso(self.reloj())))


if __name__ == "__main__":
    unittest.main()

