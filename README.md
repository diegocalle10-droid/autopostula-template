# Autopostula

Busca ofertas de LinkedIn mientras duermes y te deja por la mañana, en Telegram, un CV en PDF adaptado a cada oferta que encaja contigo. Tú solo revisas y te postulas.

https://github.com/user-attachments/assets/a64ef442-f424-4377-a880-1d90cfd11e68

<sub>Video de 50 s, todo simulado (la persona y las ofertas son ficticias). Música: Sascha Ende, ende.app (CC BY 4.0).</sub>

> **Aviso legal.** La captura usa tu propia cuenta de LinkedIn de forma automatizada, lo que va contra sus condiciones de uso. Lo haces bajo tu responsabilidad: va despacio, se para ante cualquier aviso y no usa proxies ni trucos para esconderse, pero el riesgo es tu cuenta. Recomendado: una cuenta secundaria. Este proyecto no tiene relación con LinkedIn ni con Anthropic.

## Cómo funciona

```
Tu PC (de noche)                 Neon (tu base)                      Nube
captura → evalúa → SQLite  ──►  ofertas ──► ofertas_por_redactar ──► rutina de CV (Claude) escribe cada CV
                                                                       │
Telegram ◄── GitHub Action «CV a PDF» (valida el CV, genera el PDF) ◄──┘
Bot de gestión (Project de Claude, opcional): decidir, regenerar y consultar desde el móvil
```

1. Al irte a dormir haces doble clic en `iniciar.bat`. Chrome se abre con tu sesión de LinkedIn y busca tus puestos en tus lugares, **solo ofertas abiertas con solicitud sencilla (Easy Apply)**, a un ritmo de una petición por minuto. No usa IA.
2. Cada oferta se evalúa con tus reglas (`inputs/`) y queda `apta`, `revisar` o `descartada`. Todo se sube a tu base de Neon.
3. Al terminar te avisa por Telegram y **apaga el PC 25 minutos después** (se cambia en `inputs/lotes.md`; `shutdown /a` lo cancela).
4. De madrugada, la rutina de Claude en la nube redacta un CV a medida para cada oferta apta; una Action de GitHub lo valida, genera el PDF y te lo envía por Telegram.

## Stack obligatorio

- **Claude Pro** (o superior), con la app de escritorio de Claude: la entrevista, la instalación guiada, la rutina de CV y el bot usan Claude.
- **Windows** (macOS y Linux, en una versión futura) con **Git**, **Python 3.12 o superior** (que responda a `python`) y **Google Chrome**. Si te falta alguno, la instalación guiada te lo instala.
- Una **cuenta de LinkedIn** con la interfaz en español o en inglés (recomendado: una secundaria).
- Cuentas gratuitas de **GitHub**, **Neon** y **Telegram**.
- **Energía de Windows:** la captura corre varias horas de noche. Configura «Suspender» e «Hibernar» en **Nunca** (o más horas de las que dura la captura), con cargador y sin cargador; la pantalla sí puede apagarse. Como el PC se apaga solo al terminar, no se queda encendido. La instalación guiada lo comprueba.

## Puesta en marcha

1. **Tu copia privada.** En esta página: **Use this template → Create a new repository → Private**. Tiene que ser privado: va a guardar tu CV.
2. **La entrevista (sin instalar nada).** Abre [claude.ai/code](https://claude.ai/code), conecta tu GitHub (dale acceso a tu repositorio nuevo), elígelo y escribe **«configura mi Autopostula»**. Claude te pide tu CV en PDF y te pregunta qué buscas, dónde, en qué modalidad, qué idiomas aceptas y a qué hora quieres los CV. Guion: [CONFIGURAR.md](CONFIGURAR.md).
3. **La instalación en tu PC (guiada).** Abre la app de escritorio de Claude → pestaña **Code** → una carpeta vacía, y escribe: «Clona https://github.com/&lt;tu-usuario&gt;/&lt;tu-repo&gt; aquí y sigue INSTALAR.md». Claude comprueba lo que falta y te acompaña con Neon, Telegram, LinkedIn, los secretos de GitHub y la rutina de CV, y termina con una ronda de comprobación. Guion: [INSTALAR.md](INSTALAR.md); guías con capturas de cada servicio en `guia/`.

`python cli.py doctor` te dice en cualquier momento qué falta. Mientras algún enlace de `inputs/mensajes/enlaces.md` diga `PENDIENTE`, los mensajes de Telegram lo muestran tal cual: la instalación los rellena.

## Uso diario

- **Por la noche:** doble clic en `iniciar.bat`, di cuántas horas (o Intro para las de siempre) y vete a dormir.
- **Por la mañana:** en Telegram tienes un PDF por oferta, con su enlace. Revísalo y postúlate.
- **Cambiar algo** (puestos, lugares, idiomas…): vuelve a claude.ai/code y pide «quiero cambiar mis puestos», o edita `inputs/` a mano.

## Actualizar a la última versión

Tu repositorio no se actualiza solo. La instalación ya lo dejó enlazado con la plantilla (remoto `plantilla`), así que basta con:

```
git pull plantilla main
```

Solo choca lo que hayáis cambiado los dos; en `inputs/` y `CV/base/`, quédate con lo tuyo.

## Problemas e ideas

Abre un *issue* en el repositorio de la plantilla (hay formularios para errores e ideas). Incluye la salida de `python cli.py doctor`, **nunca** tu `.env` ni tus datos.

## Licencia

MIT (ver [LICENSE](LICENSE)). Úsalo, cámbialo y compártelo; sin garantías.

## Para desarrolladores

Normas de código, pruebas y qué va en cada documento: [CLAUDE.md](CLAUDE.md). Qué hace cada módulo: su docstring.

### Comandos (`python cli.py <comando>`)

| Comando | Qué hace |
|---|---|
| `instalar`, `doctor`, `validar-cv`, `probar-titulos`, `telegram-chat-id` | Puesta en marcha y comprobaciones |
| `sesion` | Inicia o comprueba la sesión de LinkedIn |
| `run-continuo [--horas H]` | La captura (lo que lanza `iniciar.bat`) |
| `status`, `reanudar [--forzar]` | Estado del día y del disyuntor; levantar sus pausas |
| `init-db`, `plan`, `run`, `detail`, `prune`, `reevaluar` | Piezas sueltas de la captura (`--dry-run` solo muestra qué haría) |
| `online-init`, `online-subir`, `online-estado`, `online-pdf` | Neon: esquema, subida, comparación, validación y PDF de los CV |

### Parámetros: `inputs/`

| Archivo | Qué decide |
|---|---|
| `puestos.md` | Términos de búsqueda y su prioridad |
| `ubicaciones.md` | Lugares donde buscar (países, regiones, ciudades); países aceptados y excluidos |
| `modalidades.md` | Modalidades aceptadas (remoto, híbrido, presencial) |
| `prefiltro.md` | Familias de palabras del título: a qué ofertas se les pide el detalle |
| `decisiones.md` | Estado y motivo de cada caso |
| `idioma.md` | Idioma propio y vigilado; glosarios de nivel exigido |
| `lotes.md` | Ritmo, horas por defecto, cadencias, poda, escalada del 429, apagado del PC |
| `cv.md` | CV base, umbral de afinidad y tope de la rutina |
| `mensajes/` | Todo lo de Telegram: formatos, enlaces de tu instalación, emoji y textos |

### Mapa del repositorio

| Ruta | Qué es |
|---|---|
| `cli.py`, `iniciar.bat` | Punto de entrada único; lanzador de la captura |
| `CONFIGURAR.md`, `configurar/` | Guion de la entrevista; CV de ejemplo y glosarios de idioma que copia |
| `INSTALAR.md`, `guia/` | Guion de la instalación en el PC; guías con capturas de cada servicio |
| `CV/PROMPT_RUTINA.md`, `CV/PROMPT_MINIMO.md` | Instrucciones de la rutina de CV y la frase que se pega en la rutina |
| `CV/base/`, `CV/entrada/` | Tus CV base en Markdown; tu PDF, solo durante la entrevista |
| `skills-project-bot/` | El bot de gestión: prompt, orquestador y skills F1–F7 |
| `collector/comandos/` | Los comandos de `cli.py` |
| `collector/config/` | Carga y validación de `inputs/` |
| `collector/linkedin/` | La única frontera con LinkedIn: sesión, navegación y lectura de páginas |
| `collector/pipeline/` | La captura: agenda, búsquedas, detalles, disyuntor, ritmo y poda |
| `collector/filters/` | Reglas puras: título, país, idioma, decisión, validación del CV |
| `collector/db/` | Base local (SQLite) y su esquema en `migrations/` |
| `collector/online/` | Neon (subida y esquema en `migrations/`), PDF de los CV y Telegram |
| `collector/cv/`, `collector/util/` | PDF del CV; utilidades (fechas, texto, bloqueo, apagado) |
| `.github/workflows/` | `Pruebas` (en cada subida) y `CV a PDF` (valida, genera y envía los CV) |
| `tests/`, `tests/fixtures/` | Pruebas sin red, con datos de ejemplo |
| `tools/check_size.py` | Control de tamaño de archivos y funciones |
| `data/` (no versionado) | `ofertas.sqlite` (búfer local), `perfil_linkedin/` (tu sesión de LinkedIn), `.lock` |

### Decisiones de diseño

- **Sesión iniciada en LinkedIn**: con sesión funcionan el filtro de modalidad (`f_WT`) y la etiqueta de modalidad de cada oferta. Sin evasión: ni proxies ni rotación de IP; se va despacio y se para rápido.
- **Sin tope diario**: lo limitan las horas de la captura al ritmo de `lotes.md`. Un 429, captcha o verificación nunca se reintenta de inmediato: lo gobierna el disyuntor (escalada en `lotes.md`).
- **Prefiltro por título** antes de pedir el detalle (la petición escasa) y **paginación por relevancia**: la página siguiente solo si trae suficientes ofertas nuevas y suficientes títulos del perfil.
- **Las ofertas descartadas se guardan** con su motivo: nunca se repite su detalle. Las descripciones no se purgan: permiten recalibrar las reglas sin volver a pedirlas a LinkedIn.
- **La modalidad es la etiqueta de LinkedIn**; sin etiqueta vale la primera modalidad aceptada.
- **CV a medida**: emparejamiento laxo (`umbral_afinidad`) porque una persona revisa cada CV; los CV base no se mezclan. El CV vive como Markdown en Neon (`emparejamientos.cv_md`) y el PDF lo genera la Action con ReportLab, sin IA.
- **SQL solo en `db/` y `online/`**, siempre parametrizado; `inputs/` se valida al arrancar.

### Riesgos y límites

- La lectura depende del texto y de unos pocos selectores de la página (`li[data-occludable-job-id]`, el botón «Página N»), en español o en inglés; si LinkedIn cambia el marcado puede dejar de devolver resultados (`vacios_seguidos_para_alerta` búsquedas vacías seguidas activan una pausa).
- La sesión caduca: una vez por día de ejecución se comprueba y, si falló, hay aviso por Telegram y unos minutos para iniciarla en la ventana; si nadie lo hace, esa noche no hay captura.
- Ofertas y CV personales están en un servicio externo (Neon). El plan gratuito guarda poco historial y el sistema no hace copias de seguridad.
