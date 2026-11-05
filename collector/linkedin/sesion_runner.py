"""Única frontera con LinkedIn: navega con la sesión guardada de tu cuenta (Chrome visible, perfil en data/perfil_linkedin)
y devuelve listas de ofertas y detalles. Corre en este PC, sin ningún
modelo. El ritmo entre peticiones lo pone `pipeline/ritmo`; los avisos de LinkedIn salen como `LimiteError`."""
from __future__ import annotations

import random
from pathlib import Path
from typing import Callable, List, Optional

from collector.config.modelos import Config
from collector.linkedin import lectura, sesion
from collector.linkedin.errores import LimiteError, LinkedinError, NoEncontradaError, SesionError
from collector.util import reloj
from collector.util.texto import normalizar

PERFIL = ("data", "perfil_linkedin")
_ESPERA_PAGINA_MS = 60000
_SIN_RESULTADOS = "no se han encontrado|no hay resultados|no matching jobs|no results found"


class LinkedinSesion:
    def __init__(self, raiz, cfg: Config, avisar: Optional[Callable[..., None]] = None, ahora=reloj.ahora):
        self._raiz, self._cfg, self._ahora = Path(raiz), cfg, ahora
        self._avisar = avisar or (lambda clave, **datos: print(clave, datos, flush=True))
        self._perfil = self._raiz.joinpath(*PERFIL)
        self._pw = self._ctx = self._page = None
        self._lugar: Optional[tuple] = None   # (búsqueda, página) donde se quedó la lista
        self._fin_lista = False                # la página trajo el aviso de «resultados relacionados»: no hay más

    def __enter__(self) -> "LinkedinSesion":
        self.abrir()
        return self

    def __exit__(self, *_) -> None:
        self.cerrar()

    def abrir(self) -> None:
        """Abre Chrome con el perfil guardado y aplica el protocolo de sesión (una vez por día)."""
        from playwright.sync_api import sync_playwright   # import tardío: el resto del proyecto funciona sin el paquete
        self._pw = sync_playwright().start()
        self._ctx = self._pw.chromium.launch_persistent_context(str(self._perfil), channel="chrome", headless=False, no_viewport=True)
        self._page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        hoy = self._ahora().astimezone().date().isoformat()
        if not sesion.protocolo(self._page, self._perfil, hoy, self._avisar):
            self.cerrar()
            raise SesionError("SESION_NO_INICIADA", "no hay sesión válida de LinkedIn; ejecuta «python cli.py sesion»")

    def cerrar(self) -> None:
        for cierre in (lambda: self._ctx.close(), lambda: self._pw.stop()):
            try:
                cierre()
            except Exception:   # ya cerrado, o el usuario cerró la ventana
                pass
        self._ctx = self._pw = self._page = None

    def buscar(self, termino: str, ubicacion: str, jobage_dias: int, filtro_modalidad: str, pagina: int) -> List[dict]:
        busqueda = (termino, ubicacion, jobage_dias, filtro_modalidad)
        if pagina == 1:
            ubic = self._cfg.ubicacion_por_frase(ubicacion)
            if ubic is None or not ubic.geo_id:
                raise LinkedinError("SIN_GEOID", f"«{ubicacion}» no tiene geo_id en ubicaciones.md (python cli.py geoids)")
            self._fin_lista = False
            self._ir(lectura.url_busqueda(termino, ubicacion, filtro_modalidad, jobage_dias, ubic.geo_id))
        elif not self._pasar_pagina(busqueda, pagina):
            return []
        self._lugar = (busqueda, pagina)
        return self._leer_lista()

    def detalle(self, job_id: str) -> dict:
        self._ir(f"https://www.linkedin.com/jobs/view/{job_id}/")
        try:
            self._page.wait_for_function("() => /Acerca del empleo|About the job|Ya no se aceptan|no longer accepting|"
                                         "no est. disponible|no longer available|no se (ha )?encontr/i.test(document.body.innerText)",
                                         timeout=25000)
        except Exception:
            raise LinkedinError("OFERTA_SIN_CONTENIDO", f"la oferta {job_id} no mostró contenido") from None
        texto = self._page.inner_text("body")
        self._vigilar()
        descripcion = self._page.evaluate(lectura.DESCRIPCION_JS)
        if not descripcion and lectura.NO_DISPONIBLE.search(normalizar(texto)):
            raise NoEncontradaError("NOT_FOUND", f"la oferta {job_id} ya no existe")
        c = lectura.cabecera(texto, self._cfg.modalidad.etiquetas)
        return {"description": descripcion, "isActive": not lectura.CERRADA.search(texto), "employmentType": c.get("tipo_empleo"),
                "modalidad": c.get("modalidad"), "easyApply": c.get("solicitud_sencilla", False)}

    def _ir(self, url: str) -> None:
        try:
            respuesta = self._page.goto(url, wait_until="domcontentloaded", timeout=_ESPERA_PAGINA_MS)
        except Exception as e:
            raise LinkedinError("NAVEGACION", str(e)[:200]) from None
        self._vigilar(respuesta.status if respuesta else None)

    def _vigilar(self, status: Optional[int] = None) -> None:
        """Lanza el error que corresponda si LinkedIn mostró un aviso o pidió iniciar sesión otra vez."""
        try:
            texto = self._page.inner_text("body", timeout=5000)
        except Exception:
            texto = ""
        tipo = sesion.clasificar(self._page.url, status, texto)
        if tipo == "limite":
            raise LimiteError("ANTI_BOT", f"LinkedIn mostró un aviso ({status or self._page.url[:80]})")
        if tipo == "sesion":
            raise SesionError("SESION_CADUCADA", "LinkedIn pide iniciar sesión otra vez")

    def _pasar_pagina(self, busqueda: tuple, pagina: int) -> bool:
        """Pasa a la página con el botón de la paginación, como una persona. False si no hay más páginas."""
        if self._lugar != (busqueda, pagina - 1):
            raise LinkedinError("PAGINA_FUERA_DE_SECUENCIA", f"se pidió la página {pagina} sin haber leído la anterior")
        if self._fin_lista:
            return False
        boton = self._page.locator(f'button[aria-label="Página {pagina}"], button[aria-label="Page {pagina}"]')
        self._page.evaluate("s => document.querySelector(s)?.scrollIntoView({block: 'end'})", lectura.PAGINACION)
        self._page.wait_for_timeout(random.uniform(800, 1600))
        if boton.count() == 0:
            return False
        primera = self._page.evaluate(f"s => {{ const e = document.querySelector(s); return e && ({lectura.ID_JS})(e); }}",
                                      lectura.TARJETA)
        boton.first.click()
        try:
            self._page.wait_for_function(f"([s, p]) => {{ const e = document.querySelector(s); return e && ({lectura.ID_JS})(e) !== p; }}",
                                         arg=[lectura.TARJETA, primera], timeout=25000)
        except Exception:
            raise LinkedinError("PAGINA_NO_CAMBIO", f"la página {pagina} no cambió") from None
        return True

    def _leer_lista(self) -> List[dict]:
        try:
            self._page.wait_for_selector(lectura.TARJETA, timeout=25000)
        except Exception:
            self._vigilar()
            if self._page.locator(f"text=/{_SIN_RESULTADOS}/i").count():
                return []
            raise LinkedinError("LISTA_SIN_TARJETAS", f"la página no trae lista: {self._page.url[:100]}") from None
        self._vigilar()
        return self._cargar_tarjetas()

    def _cargar_tarjetas(self) -> List[dict]:
        """La lista solo pinta las tarjetas a la vista: baja poco a poco y las acumula hasta tener las de la página.
        Las que van tras el aviso de «resultados relacionados» no cumplen los filtros: no cuentan y no hay más páginas."""
        vistas: dict = {}
        total = estables = 0
        for _ in range(60):
            crudas = self._page.evaluate(lectura.TARJETAS_JS, lectura.TARJETA)
            exactas = [c for c in crudas if not (len(c) > 2 and c[2])]
            self._fin_lista = len(exactas) < len(crudas)
            for job_id, texto, *_ in exactas:
                t = lectura.tarjeta(job_id, texto, self._cfg.modalidad.etiquetas, self._ahora())
                if t and job_id not in vistas:
                    vistas[job_id] = t
            falta = next((c[0] for c in exactas if c[0] not in vistas), None)
            estables = estables + 1 if (len(crudas) == total and falta is None) else 0
            total = len(crudas)
            if estables >= 2 or len(vistas) >= lectura.POR_PAGINA or (self._fin_lista and falta is None):
                break
            self._page.evaluate("""([p, i]) => document.querySelector(`[componentkey="${p}${i}"][role="button"]`)
                                   ?.scrollIntoView({block: 'center'})""", [lectura.PREFIJO_ID, falta or crudas[-1][0]])
            self._page.wait_for_timeout(random.uniform(700, 1500))
        return list(vistas.values())
