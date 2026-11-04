"""Estructuras de la configuración leída de inputs/*.md."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple


class ConfigError(Exception):
    """La configuración de inputs/ está incompleta o es inválida."""


@dataclass(frozen=True)
class Ubicacion:
    tipo: str                      # pais | region
    frase: str
    pais_esperado: Optional[str]   # None para regiones


@dataclass(frozen=True)
class Termino:
    prioridad: int
    termino: str


@dataclass(frozen=True)
class Modalidad:
    nombre: str
    filtro: str                      # valor del filtro de modalidad de LinkedIn (f_WT)
    aceptada: bool
    etiquetas: Tuple[str, ...]       # cómo la rotula LinkedIn en la tarjeta y en la oferta (normalizadas)


@dataclass(frozen=True)
class ConfigModalidad:
    modalidades: Tuple[Modalidad, ...]

    @property
    def aceptadas(self) -> FrozenSet[str]:
        return frozenset(m.nombre for m in self.modalidades if m.aceptada)

    @property
    def busqueda(self) -> Modalidad:
        """La primera aceptada: es la que se atribuye a una oferta que LinkedIn no rotula."""
        return next(m for m in self.modalidades if m.aceptada)

    @property
    def filtro(self) -> str:
        """El filtro de modalidad (f_WT) que se pide a LinkedIn: todas las aceptadas a la vez («2,3»)."""
        return ",".join(m.filtro for m in self.modalidades if m.aceptada)

    @property
    def etiquetas(self) -> Dict[str, str]:
        """Etiqueta normalizada → nombre de la modalidad."""
        return {e: m.nombre for m in self.modalidades for e in m.etiquetas}


@dataclass(frozen=True)
class ConfigIdioma:
    pasa: Tuple[str, ...]
    rechaza: Tuple[str, ...]
    mcer: Dict[str, str]                      # nivel normalizado -> pasa | rechaza
    negaciones: Tuple[str, ...]
    ventana_mcer: int
    ventana_negacion: int
    umbral: float
    minimo_palabras: int
    propio: str                               # código del idioma en el que quieres trabajar
    vigilado: str                             # código del idioma cuyo nivel se exige
    alias_vigilado: Tuple[str, ...]           # cómo se nombra el idioma vigilado en un anuncio
    palabras: Dict[str, FrozenSet[str]]       # código -> palabras funcionales (descripciones)
    palabras_titulo: Dict[str, FrozenSet[str]]


class Lotes:
    """Acceso tipado a inputs/lotes.md."""

    def __init__(self, valores: Dict[str, str]):
        self._v = valores

    def texto(self, clave: str) -> str:
        try:
            return self._v[clave]
        except KeyError:
            raise ConfigError(f"lotes.md: falta la clave «{clave}»") from None

    def entero(self, clave: str) -> int:
        try:
            return int(self.texto(clave))
        except ValueError:
            raise ConfigError(f"lotes.md: «{clave}» debe ser un entero") from None

    def decimal(self, clave: str) -> float:
        try:
            return float(self.texto(clave))
        except ValueError:
            raise ConfigError(f"lotes.md: «{clave}» debe ser un número") from None


@dataclass(frozen=True)
class Escalon429:
    ocurrencias: int            # 429 que activan el escalón (el actual cuenta)
    ventana_dias: int           # 0 = hoy
    accion: str                 # pausa | hasta_manana | parada_total
    horas: Optional[int]


@dataclass(frozen=True)
class ReglaDecision:
    condicion: str
    estado: str
    motivo: Optional[str]


@dataclass(frozen=True)
class ReglaIngreso:
    accion: str                 # descartar | esperar | evaluar
    motivo: str

    def motivo_para(self, pais: Optional[str], original: str) -> str:
        return self.motivo.format(pais=pais or "", original=original)


@dataclass(frozen=True)
class ConfigDecisiones:
    reglas: Tuple[ReglaDecision, ...]
    ingreso: Dict[str, ReglaIngreso]      # situación -> regla

    def regla(self, condicion: str) -> ReglaDecision:
        return next(r for r in self.reglas if r.condicion == condicion)


@dataclass(frozen=True)
class FamiliaTitulo:
    """Un grupo de raíces de palabra con un peso: positivo si acerca el título al perfil, negativo si lo aleja."""
    nombre: str
    peso: int
    raices: Tuple[str, ...]                        # «x*» = palabra que empieza por x; sin asterisco, palabra o frase exacta


@dataclass(frozen=True)
class ConfigPrefiltro:
    """Criterios para decidir a qué ofertas se les pide el detalle y en qué orden (inputs/prefiltro.md)."""
    puntuacion_minima: int
    familias: Tuple[FamiliaTitulo, ...]
    prioridad_pais: Dict[str, int]                 # país aceptado -> orden (1 = primero)
    prioridad_pais_defecto: int
    orden: Tuple[Tuple[str, str], ...]             # (criterio, asc|desc)


@dataclass(frozen=True)
class CvBase:
    id: str
    archivo: str            # ruta relativa a la raíz del proyecto
    perfil: str


@dataclass(frozen=True)
class ConfigCv:
    """CV base y umbral de afinidad (inputs/cv.md)."""
    cvs: Tuple[CvBase, ...]
    umbral_afinidad: int

    def cv(self, cv_id: str) -> Optional[CvBase]:
        return next((c for c in self.cvs if c.id == cv_id), None)


@dataclass(frozen=True)
class ConfigMensajes:
    """Ajustes y plantillas de Telegram (inputs/mensajes/)."""
    ajustes: Dict[str, str]
    plantillas: Dict[str, str]


@dataclass
class Config:
    ubicaciones: List[Ubicacion]
    paises_aceptados: FrozenSet[str]
    terminos: List[Termino]
    modalidad: ConfigModalidad
    idioma: ConfigIdioma
    lotes: Lotes
    prefiltro: ConfigPrefiltro
    decisiones: ConfigDecisiones
    escalada_429: Tuple[Escalon429, ...]
    cv: ConfigCv
    cadencias: Dict[int, int] = field(default_factory=dict)   # prioridad -> días
    paises_excluidos: FrozenSet[str] = frozenset()

    def ubicacion_por_frase(self, frase: str) -> Optional[Ubicacion]:
        return next((u for u in self.ubicaciones if u.frase == frase), None)

    def cadencia(self, prioridad: int) -> int:
        try:
            return self.cadencias[prioridad]
        except KeyError:
            raise ConfigError(f"lotes.md: falta la cadencia de la prioridad {prioridad}") from None
