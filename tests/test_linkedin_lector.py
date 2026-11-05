"""Lector de LinkedIn con sesión (`buscar`, `detalle`, `_cargar_tarjetas`) contra una página falsa. Sin red ni navegador."""
import unittest
from datetime import datetime, timezone

from collector.linkedin.errores import LimiteError, LinkedinError, NoEncontradaError
from collector.linkedin.sesion_runner import LinkedinSesion
from tests.ayudas import config

AHORA = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
CABECERA = "Acme\n\nAnalista de datos\n\n México  · hace 3 días\n\nEn remoto\nJornada completa\nSolicitud sencilla\nGuardar"


def _tarjeta(i):
    return [str(i), f"Analista {i}\nAnalista {i}\nAcme\nMéxico (En remoto)\nHace 2 horas\nSolicitud sencilla"]


class Locator:
    def __init__(self, cantidad):
        self._cantidad = cantidad

    def count(self):
        return self._cantidad

    @property
    def first(self):
        return self

    def click(self):
        pass


class PaginaFalsa:
    """Responde lo justo a lo que pide el lector. `tandas` son las lecturas sucesivas de las tarjetas pintadas."""

    def __init__(self, texto="", tandas=(), descripcion="", espera_falla=False, sin_resultados=False, status=200):
        self.url, self.texto, self.tandas = "https://www.linkedin.com/jobs/search/", texto, list(tandas)
        self.descripcion, self.espera_falla, self.sin_resultados, self.status = descripcion, espera_falla, sin_resultados, status
        self.visitas, self.desplazamientos = [], 0

    def goto(self, url, **_):
        self.visitas.append(url)
        self.url = url
        return type("R", (), {"status": self.status})()

    def inner_text(self, *_, **__):
        return self.texto

    def wait_for_function(self, *_, **__):
        if self.espera_falla:
            raise TimeoutError

    wait_for_selector = wait_for_function

    def wait_for_timeout(self, *_):
        pass

    def locator(self, selector):
        return Locator(1 if (self.sin_resultados and "text=" in selector) else 0)

    def evaluate(self, js, arg=None):
        if "querySelectorAll(s)" in js and "map(" in js:
            return self.tandas.pop(0) if len(self.tandas) > 1 else self.tandas[0]
        if "scrollIntoView" in js:
            self.desplazamientos += 1
            return None
        return self.descripcion


def lector(**pagina):
    f = LinkedinSesion(".", config(), ahora=lambda: AHORA)
    f._page = PaginaFalsa(**pagina)
    return f


class Buscar(unittest.TestCase):
    def test_la_pagina_1_navega_a_la_url_de_busqueda_y_lee_las_tarjetas(self):
        f = lector(tandas=[[_tarjeta(1), _tarjeta(2)]])
        ofertas = f.buscar("business analyst", "Mexico", 30, "2", 1)
        self.assertEqual([o["title"] for o in ofertas], ["Analista 1", "Analista 2"])
        self.assertIn("f_AL=true", f._page.visitas[0])
        self.assertIn("business+analyst", f._page.visitas[0])
        self.assertIn("geoId=103323778", f._page.visitas[0])   # sin geoId la lista aplica la ubicación de la cuenta

    def test_una_ubicacion_sin_geo_id_falla_sin_navegar(self):
        f = lector()
        with self.assertRaises(LinkedinError) as e:
            f.buscar("x", "Atlantida", 30, "2", 1)
        self.assertEqual(e.exception.codigo, "SIN_GEOID")
        self.assertEqual(f._page.visitas, [])

    def test_las_tarjetas_repetidas_en_varias_lecturas_se_acumulan_sin_duplicar(self):
        f = lector(tandas=[[_tarjeta(1), _tarjeta(2)], [_tarjeta(1), _tarjeta(2), _tarjeta(3)]])
        ofertas = f._cargar_tarjetas()
        self.assertEqual(len(ofertas), 3)
        self.assertGreater(f._page.desplazamientos, 0)

    def test_tras_el_aviso_de_resultados_relacionados_no_cuentan_ni_hay_mas_paginas(self):
        f = lector(tandas=[[_tarjeta(1) + [False], _tarjeta(2) + [False], _tarjeta(3) + [True], _tarjeta(4) + [True]]])
        ofertas = f.buscar("x", "Mexico", 30, "2", 1)
        self.assertEqual([o["id"] for o in ofertas], ["1", "2"])
        self.assertEqual(f.buscar("x", "Mexico", 30, "2", 2), [])   # sin buscar el botón de la página 2

    def test_solo_resultados_relacionados_es_una_pagina_vacia(self):
        f = lector(tandas=[[_tarjeta(1) + [True], _tarjeta(2) + [True]]])
        self.assertEqual(f.buscar("x", "Mexico", 30, "2", 1), [])

    def test_una_tarjeta_sin_pintar_se_pide_otra_vez_al_bajar(self):
        f = lector(tandas=[[_tarjeta(1), ["2", "  "]], [_tarjeta(1), _tarjeta(2)]])
        self.assertEqual({o["id"] for o in f._cargar_tarjetas()}, {"1", "2"})

    def test_sin_tarjetas_y_con_aviso_de_no_hay_resultados_devuelve_lista_vacia(self):
        self.assertEqual(lector(espera_falla=True, sin_resultados=True).buscar("x", "Mexico", 30, "2", 1), [])

    def test_sin_tarjetas_y_sin_aviso_es_un_error(self):
        with self.assertRaises(LinkedinError) as e:
            lector(espera_falla=True).buscar("x", "Mexico", 30, "2", 1)
        self.assertEqual(e.exception.codigo, "LISTA_SIN_TARJETAS")

    def test_un_429_al_navegar_es_limite(self):
        with self.assertRaises(LimiteError):
            lector(status=429).buscar("x", "Mexico", 30, "2", 1)


class Detalle(unittest.TestCase):
    def test_oferta_abierta_con_cabecera_y_descripcion(self):
        d = lector(texto=CABECERA, descripcion="Texto de la oferta").detalle("123")
        self.assertEqual((d["description"], d["isActive"], d["modalidad"], d["easyApply"], d["employmentType"]),
                         ("Texto de la oferta", True, "remoto", True, "Full-time"))

    def test_oferta_que_ya_no_acepta_solicitudes_se_marca_cerrada(self):
        d = lector(texto=CABECERA + "\nYa no se aceptan solicitudes", descripcion="Texto").detalle("123")
        self.assertFalse(d["isActive"])

    def test_oferta_borrada_es_no_encontrada(self):
        with self.assertRaises(NoEncontradaError):
            lector(texto="Esta oferta ya no está disponible", descripcion="").detalle("123")

    def test_pagina_que_no_muestra_contenido_es_un_error(self):
        with self.assertRaises(LinkedinError) as e:
            lector(espera_falla=True).detalle("123")
        self.assertEqual(e.exception.codigo, "OFERTA_SIN_CONTENIDO")

    def test_un_aviso_de_linkedin_al_abrir_el_detalle_es_limite(self):
        with self.assertRaises(LimiteError):
            lector(texto="Detectamos actividad inusual en tu cuenta", status=999).detalle("123")


if __name__ == "__main__":
    unittest.main()
