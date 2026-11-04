# Autopostula

Busca ofertas de LinkedIn mientras duermes y te deja por la mañana, en Telegram, un CV en PDF adaptado a cada oferta que encaja contigo. Tú solo revisas y te postulas.

> **Aviso legal.** La captura usa tu propia cuenta de LinkedIn de forma automatizada, lo que va contra sus condiciones de uso. Lo haces bajo tu responsabilidad: va despacio (una petición por minuto), se para ante cualquier aviso y no usa proxies ni trucos para esconderse, pero el riesgo es tu cuenta. Recomendado: una cuenta secundaria. Este proyecto no tiene relación con LinkedIn ni con Anthropic.

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
3. Al terminar te avisa por Telegram y **apaga el PC 25 minutos después** (`shutdown /a` lo cancela).
4. De madrugada, la rutina de Claude en la nube redacta un CV a medida para cada oferta apta; una Action de GitHub lo valida, genera el PDF y te lo envía por Telegram.

## Stack obligatorio

- **Claude Pro** (o superior), con la app de escritorio de Claude: la entrevista, la instalación guiada, la rutina de CV y el bot usan Claude.
- **Windows** (macOS y Linux, en una versión futura) con **Git**, **Python 3.12 o superior** (que responda a `python`) y **Google Chrome**. Si te falta alguno, la instalación guiada te lo instala.
- Una **cuenta de LinkedIn** con la interfaz en español o en inglés (recomendado: una secundaria).
- Cuentas gratuitas de **GitHub**, **Neon** y **Telegram**.
- **Energía de Windows:** la captura corre varias horas de noche. Configura «Suspender» e «Hibernar» en **Nunca** (o más horas de las que dura la captura), con cargador y sin cargador; la pantalla sí puede apagarse. Al terminar, el PC se apaga solo 25 minutos después, así que no se queda encendido. La instalación guiada lo comprueba.

## Puesta en marcha

1. **Tu copia privada.** En esta página: **Use this template → Create a new repository → Private**. Tiene que ser privado: va a guardar tu CV.
2. **La entrevista (sin instalar nada).** Abre [claude.ai/code](https://claude.ai/code), conecta tu GitHub (dale acceso a tu repositorio nuevo), elígelo y escribe **«configura mi Autopostula»**. Claude te pide tu CV en PDF y te pregunta qué buscas, dónde, en qué modalidad, qué idiomas aceptas y a qué hora quieres los CV. Guion: [CONFIGURAR.md](CONFIGURAR.md).
3. **La instalación en tu PC (guiada).** Abre la app de escritorio de Claude → pestaña **Code** → una carpeta vacía, y escribe: «Clona https://github.com/&lt;tu-usuario&gt;/&lt;tu-repo&gt; aquí y sigue INSTALAR.md». Claude comprueba lo que falta y te acompaña con Neon, Telegram, LinkedIn, los secretos de GitHub y la rutina de CV, y termina activando el envío diario cuando todo funciona. Guion: [INSTALAR.md](INSTALAR.md); guías con capturas de cada servicio en `guia/`.

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

## Referencia

| Comando | Qué hace |
|---|---|
| `instalar`, `doctor`, `validar-cv`, `probar-titulos`, `telegram-chat-id` | Puesta en marcha y comprobaciones |
| `sesion` | Inicia o comprueba la sesión de LinkedIn |
| `run-continuo [--horas H]` | La captura (lo que lanza `iniciar.bat`) |
| `status`, `reanudar [--forzar]` | Estado del día y del disyuntor; levantar sus pausas |
| `init-db`, `plan`, `run`, `detail`, `prune`, `reevaluar`, `registrar-externas` | Piezas sueltas de la captura (`--dry-run` solo muestra qué haría) |
| `online-init`, `online-subir`, `online-estado`, `online-pdf` | Neon: esquema, subida, comparación, validación y PDF de los CV |

### Parámetros: `inputs/` (única fuente; el código no tiene ningún texto ni regla escritos)

| Archivo | Qué decide |
|---|---|
| `puestos.md` | Términos de búsqueda y su prioridad |
| `ubicaciones.md` | Lugares donde buscar (países, regiones, ciudades); países aceptados y excluidos |
| `modalidades.md` | Modalidades aceptadas (remoto, híbrido, presencial) |
| `prefiltro.md` | Familias de palabras del título: a qué ofertas se les pide el detalle |
| `decisiones.md` | Estado y motivo de cada caso |
| `idioma.md` | Idioma propio y vigilado; glosarios de nivel exigido |
| `lotes.md` | Ritmo, horas por defecto, cadencias, poda, escalada del 429, apagado del PC |
| `cv.md` | CV base y umbral de afinidad |
| `mensajes/` | Todo lo de Telegram: formatos, enlaces de tu instalación, emoji y textos |

### Mapa de archivos

| Ruta | Qué es |
|---|---|
| `cli.py`, `iniciar.bat` | Punto de entrada único; lanzador de la captura |
| `CONFIGURAR.md`, `configurar/` | Guion de la entrevista; CV de ejemplo y glosarios de idioma que copia |
| `INSTALAR.md`, `guia/` | Guion de la instalación en el PC; guías con capturas de cada servicio |
| `CV/PROMPT_RUTINA.md`, `CV/PROMPT_MINIMO.md` | Instrucciones de la rutina de CV (única fuente) y lo único que se pega en la rutina |
| `CV/base/`, `CV/entrada/` | Tus CV base en Markdown; tu PDF solo durante la entrevista |
| `skills-project-bot/` | El bot de gestión: prompt, orquestador y skills F1–F7 |
| `.github/workflows/` | `Pruebas` (en cada subida) y `CV a PDF` (valida, genera y envía los CV) |
| `tests/`, `tests/fixtures/` | Pruebas sin red, con datos de ejemplo |
| `tools/check_size.py` | Control de tamaño de archivos y funciones |
| `data/` (no versionado) | `ofertas.sqlite` (búfer local), `perfil_cuenta_b/` (tu sesión de LinkedIn), `.lock` |

### Código (`collector/`)

| Módulo | Qué hace |
|---|---|
| `collector/comandos/captura.py` | Lo que rodea a run-continuo: preguntar las horas, subir a Neon al arrancar y al terminar, y avisar por Telegram |
| `collector/comandos/instalacion.py` | Puesta en marcha: instalar, validar-cv, telegram-chat-id y doctor ampliado |
| `collector/comandos/datos.py` | Comandos que no hacen peticiones a LinkedIn: init-db, plan, prune, status, doctor, reanudar, registrar-externas |
| `collector/comandos/ejecucion.py` | Comandos que hacen peticiones a LinkedIn: run, detail y run-continuo |
| `collector/comandos/online.py` | Comandos de la base online (Neon): online-init, online-subir, online-pdf y online-estado |
| `collector/config/cargar.py` | Carga y valida inputs/*.md |
| `collector/config/modelos.py` | Estructuras de la configuración leída de inputs/*.md |
| `collector/config/textos.py` | Carga y valida inputs/mensajes/*.md: ajustes y plantillas de Telegram |
| `collector/cv/render.py` | Markdown de un CV -> PDF apto para ATS: una columna, texto negro seleccionable, sin tablas ni imágenes |
| `collector/db/combinaciones_repo.py` | Acceso a `combinaciones`: la agenda de búsquedas (qué toca buscar y cuándo) |
| `collector/db/connection.py` | Conexión SQLite |
| `collector/db/consultas_repo.py` | Acceso a `consultas` (diario de peticiones) y `hallazgos` (qué consulta encontró qué oferta) |
| `collector/db/eventos_repo.py` | Acceso a `eventos`: el registro de incidentes que alimenta el disyuntor |
| `collector/db/externas_repo.py` | Acceso a `peticiones_externas`: peticiones a LinkedIn hechas fuera del recolector |
| `collector/db/migrar.py` | Migraciones numeradas |
| `collector/db/ofertas_repo.py` | Acceso a la tabla `ofertas` y a sus keywords |
| `collector/estados.py` | Vocabulario interno del sistema: estados de una oferta |
| `collector/filters/cv.py` | Reglas puras sobre el Markdown de un CV reescrito: marcadores internos, defectos de estilo y nombres de carpeta |
| `collector/filters/cv_datos.py` | Datos que un CV reescrito no puede cambiar respecto a su CV base: nombre, contacto, empresa y fechas de cada puesto, |
| `collector/filters/decision.py` | Decisión sobre una oferta con su detalle: aplica las reglas de inputs/decisiones.md |
| `collector/filters/evaluar.py` | Evaluación de una oferta con su detalle: idioma, nivel exigido, modalidad (la etiqueta de LinkedIn), keywords y decisión |
| `collector/filters/huella.py` | Huella de una vacante: detecta republicaciones que LinkedIn publica con un id nuevo |
| `collector/filters/idioma.py` | Idioma de un título o de una descripción, y nivel exigido del idioma vigilado |
| `collector/filters/keywords.py` | Palabras clave de una oferta: los términos de inputs/puestos.md que aparecen en su descripción |
| `collector/filters/pais.py` | País de una oferta a partir del texto de ubicación que devuelve LinkedIn |
| `collector/filters/titulo.py` | Puntuación de un título de oferta por familias de raíces (inputs/prefiltro.md) |
| `collector/linkedin/errores.py` | Errores de la frontera con LinkedIn |
| `collector/linkedin/lectura.py` | Lectura del texto de las páginas de LinkedIn con sesión: tarjetas de la lista y cabecera de la oferta |
| `collector/linkedin/sesion.py` | Protocolo de sesión de LinkedIn: una vez cada día de ejecución se abre el inicio y se comprueba que la sesión vale |
| `collector/linkedin/sesion_runner.py` | Única frontera con LinkedIn: navega con la sesión guardada de tu cuenta (Chrome visible, perfil en data/perfil_cuenta_b) |
| `collector/online/avisos.py` | Bandeja de salida de mensajes de texto en Neon (`avisos`) |
| `collector/online/conexion.py` | Conexión a Neon |
| `collector/online/consultas.py` | Consultas a Neon que usan la captura y los mensajes: una sola definición de «ofertas por revisar» |
| `collector/online/esquema.py` | Migraciones numeradas del esquema de Neon (NNN_nombre.sql); la versión vive en `esquema_version` |
| `collector/online/mensajes.py` | Mensajes de Telegram |
| `collector/online/notificador.py` | Único punto de salida a Telegram: carga el token y el chat una sola vez y envía textos y PDF |
| `collector/online/pdfs.py` | Validación y PDF de los CV que redactó la rutina (estado `redactada` en Neon) |
| `collector/online/rutina.py` | Lo que la Action comunica de la rutina, calculado con consultas a Neon (la rutina no escribe mensajes): |
| `collector/online/subir.py` | Subida de la SQLite local a Neon |
| `collector/online/telegram.py` | Envío a Telegram (HTML): textos (sendMessage) y el PDF del CV con su pie (sendDocument, hasta 50 MB) |
| `collector/pipeline/batch_runner.py` | Ejecuta una tanda de búsquedas respetando ritmo y disyuntor |
| `collector/pipeline/breaker.py` | Disyuntor: decide si se pueden lanzar peticiones y registra los incidentes |
| `collector/pipeline/cuota.py` | Recuento de las peticiones a LinkedIn de hoy (informativo: no hay tope diario) |
| `collector/pipeline/detail_runner.py` | Pide el detalle de las ofertas elegibles y las evalúa (idioma, modalidad, keywords, decisión) |
| `collector/pipeline/flujo.py` | Flujo continuo: una sola cadena de peticiones que alterna búsquedas y detalles para que no se acumulen ofertas |
| `collector/pipeline/ingest.py` | Guarda en la base de datos los resultados de una búsqueda y aplica el filtro de título (inputs/prefiltro.md): |
| `collector/pipeline/plan_builder.py` | Construye la agenda de búsquedas: cada término × cada ubicación válida |
| `collector/pipeline/prune.py` | Poda por rendimiento: espacia lo que no aporta y recupera lo que vuelve a aportar |
| `collector/pipeline/reevaluar.py` | Reevaluar con las reglas actuales (inputs/) las ofertas aptas o por revisar que ya tienen descripción |
| `collector/pipeline/ritmo.py` | Ritmo de las peticiones: pausas aleatorias dentro de un lote y entre lotes |
| `collector/pipeline/seleccion.py` | Selección de las ofertas a las que se les pide el detalle |
| `collector/util/apagado.py` | Apagado del PC al terminar la captura (solo Windows): programa `shutdown /s` con un margen para poder cancelarlo |
| `collector/util/bloqueo.py` | Un solo proceso a la vez: archivo de bloqueo con caducidad, para que dos ejecuciones no se pisen |
| `collector/util/md_tables.py` | Lee las tablas markdown de inputs/*.md: {clave_de_seccion: [fila, ...]} |
| `collector/util/reloj.py` | Fechas y horas |
| `collector/util/texto.py` | Normalización y búsqueda de expresiones en texto |
| `collector/db/migrations/`, `collector/online/migrations/` | Esquema de SQLite (001–004) y de Neon (001–004): la única fuente de tablas y columnas; en `001_neon.sql`, quién escribe cada tabla |

## Decisiones de diseño que importan

- **Sesión de tu cuenta** en vez de acceso de invitado: con sesión funcionan el filtro de modalidad (`f_WT`) y la etiqueta de modalidad de cada oferta. El acceso con sesión va contra las condiciones de LinkedIn: lo que se arriesga es la cuenta y la IP. Sin evasión: ni proxies ni rotación de IP; se va despacio y se para rápido.
- **Sin tope diario**: lo limitan las horas de la captura al ritmo de `lotes.md`. Un 429, captcha o verificación nunca se reintenta de inmediato: lo gobierna el disyuntor (escalada en `lotes.md`).
- **Prefiltro por título** antes de pedir el detalle (la petición escasa) y **paginación por relevancia**: la página siguiente solo si trae suficientes ofertas nuevas y suficientes títulos del perfil.
- **Las ofertas descartadas se guardan** con su motivo: nunca se repite su detalle. Las descripciones no se purgan: permiten recalibrar las reglas sin volver a pedirlas a LinkedIn.
- **La modalidad es la etiqueta de LinkedIn**; sin etiqueta vale la de la búsqueda.
- **CV a medida**: matching laxo (umbral de `inputs/cv.md`) porque una persona revisa cada oferta; los CV base no se unifican. El CV vive como Markdown en Neon (`emparejamientos.cv_md`) y el PDF lo genera la Action con ReportLab, sin IA.
- **SQL solo en `db/` y `online/`**, siempre parametrizado; `inputs/` se valida al arrancar.

## Riesgos y límites

- La lectura depende del texto y de unos pocos selectores de la página (`li[data-occludable-job-id]`, el botón «Página N»); si LinkedIn cambia el marcado puede dejar de devolver resultados (tres búsquedas vacías seguidas activan una pausa).
- La sesión caduca: una vez por día de ejecución se comprueba y, si falló, hay aviso por Telegram y 10 minutos para iniciarla en la ventana.
- Ofertas y CV personales están en un servicio externo (Neon). El plan gratuito de Neon guarda poco historial y el sistema no hace copias de seguridad.
