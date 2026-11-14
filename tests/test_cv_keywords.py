"""Runbook v7: CV compuesto con la plantilla, cobertura de keywords y afinidad con evidencia real del CV base."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from collector.cv.componer import componer, leer_base
from collector.filters.cv import problemas
from collector.filters.cv_cobertura import afinidad, errores_keywords, faltantes, respaldo_efectivo
from collector.filters.cv_datos import verificar_datos
from tests.ayudas import RAIZ, config
from tests.falso_neon import FalsoNeon, esquema_neon_sqlite

BASE = (RAIZ / "CV/base/data_analytics.md").read_text(encoding="utf-8")
PLANTILLA = (RAIZ / "CV/plantilla.md").read_text(encoding="utf-8")
EVIDENCIA = "Automaticé la carga de datos desde tres sistemas"
KW = ["Azure Synapse Analytics", "PySpark", "Delta Lake", "Lakehouse", "Medallion", "T-SQL",
      "programación orientada a objetos", "ETL/ELT", "modelado dimensional", "orquestación basada en metadatos"]


def contenido(vinetas_extra=()):
    return {"titular": "Ingeniero de Datos Azure",
            "perfil": "Ingeniero de datos en el ecosistema Azure.",
            "puestos": [{"cargo": "Ingeniero de Datos", "vinetas": [
                            "Diseñé pipelines con Azure Synapse Analytics y PySpark sobre un Lakehouse con Delta Lake.",
                            "Estructuré capas Medallion y un modelado dimensional para la analítica.",
                            *vinetas_extra]},
                        {"cargo": "Analista de Datos", "vinetas": [
                            "Optimicé consultas y procedimientos en T-SQL y procesos ETL/ELT.",
                            "Programé módulos reutilizables con POO en Python."]},
                        {"cargo": "Analista Funcional", "vinetas": [
                            "Mantuve una orquestación basada en metadatos para las cargas."]}],
            "stack": ["**Datos:** SQL · Python"]}


def keywords():
    salida = [{"kw": k, "variantes": [], "tipo": "herramienta", "respaldo": "ninguno", "evidencia": ""} for k in KW]
    salida[6]["variantes"] = ["POO"]
    salida[8].update(respaldo="directo", evidencia=EVIDENCIA)
    return salida


class Componer(unittest.TestCase):
    def test_los_datos_fijos_salen_del_cv_base(self):
        md, errores = componer(PLANTILLA, BASE, contenido())
        self.assertEqual(errores, [])
        self.assertEqual(verificar_datos(BASE, md), [])
        self.assertEqual(problemas(md), [])
        base = leer_base(BASE)
        for fijo in [base.nombre, base.contacto, base.idiomas, *base.puestos]:
            self.assertIn(fijo, md)
        self.assertNotIn("{{", md)
        self.assertNotIn("<!--", md)

    def test_numero_de_puestos_distinto_no_se_compone(self):
        c = contenido()
        c["puestos"].pop()
        md, errores = componer(PLANTILLA, BASE, c)
        self.assertEqual(md, "")
        self.assertIn("3 puestos", errores[0])


class Cobertura(unittest.TestCase):
    def test_cuenta_solo_las_vinetas_de_experiencia_y_acepta_variantes(self):
        md, _ = componer(PLANTILLA, BASE, contenido())
        self.assertEqual(faltantes(keywords(), md), [])
        perfil_solo = md.replace("Azure Synapse Analytics y ", "")
        self.assertEqual(faltantes(keywords(), perfil_solo), ["Azure Synapse Analytics"])

    def test_evidencia_que_no_esta_en_el_base_no_respalda(self):
        self.assertEqual(respaldo_efectivo({"respaldo": "directo", "evidencia": EVIDENCIA}, BASE), "directo")
        self.assertEqual(respaldo_efectivo({"respaldo": "directo", "evidencia": "Usé Databricks"}, BASE), "ninguno")

    def test_afinidad_con_la_formula_del_runbook(self):
        kws = keywords()
        kws[0].update(respaldo="parcial", evidencia=EVIDENCIA)
        self.assertEqual(afinidad(kws, BASE)[0], 15)   # (1 + 0,5) / 10

    def test_numero_de_keywords(self):
        self.assertEqual(errores_keywords(keywords(), 10, 15), [])
        self.assertIn("entre 10 y 15", errores_keywords(keywords()[:3], 10, 15)[0])


class Action(unittest.TestCase):
    def setUp(self):
        self.neon = sqlite3.connect(":memory:")
        self.addCleanup(self.neon.close)
        self.neon.executescript(esquema_neon_sqlite())
        self.neon.executescript("CREATE TABLE avisos (aviso_id INTEGER PRIMARY KEY, creado_en TEXT, texto TEXT NOT NULL, "
                                "enviado_en TEXT, tipo TEXT NOT NULL DEFAULT 'texto');")
        self.neon.execute("INSERT INTO ofertas (job_id,url,titulo,empresa,fecha_hallazgo,ultima_vista,modalidad,estado) "
                          "VALUES ('1','u','Ingeniero de Datos','Acme','x','x','remoto','apta')")

    def pasada(self, c, enviar=None):
        self.neon.execute("INSERT INTO emparejamientos (job_id,estado,cv_id,afinidad,keywords,contenido,emparejado_en) "
                          "VALUES ('1','redactada','data_analytics',90,?,?,'t')",
                          (json.dumps(keywords()), json.dumps(c)))
        from collector.online import pdfs
        return pdfs.procesar(FalsoNeon(self.neon), config(), RAIZ, Path(tempfile.mkdtemp()), "2026-11-12T00:00:00Z",
                             log=lambda m: None, enviar=enviar)

    def test_cv_con_todas_las_keywords_se_compone_valida_y_recalcula_afinidad(self):
        enviados = []
        self.assertEqual(self.pasada(contenido(), lambda p, t: enviados.append(t))["validadas"], ["1"])
        cv_md, af, cubiertos = self.neon.execute("SELECT cv_md, afinidad, requisitos_cubiertos FROM emparejamientos").fetchone()
        self.assertIn("Azure Synapse Analytics", cv_md)
        self.assertEqual((af, cubiertos), (10, "modelado dimensional"))
        self.assertIn("afinidad 10 %", enviados[0])

    def test_falta_una_keyword_en_las_vinetas_y_se_rechaza_con_su_nombre(self):
        c = contenido()
        c["puestos"][2]["vinetas"] = ["Documenté integraciones con SAP."]
        self.assertEqual(self.pasada(c)["rechazadas"], ["1"])
        estado, rechazo = self.neon.execute("SELECT estado, rechazo FROM emparejamientos").fetchone()
        self.assertEqual(estado, "rechazada")
        self.assertIn("orquestación basada en metadatos", rechazo)
        self.assertIn("cobertura 90 %", rechazo)


if __name__ == "__main__":
    unittest.main()
