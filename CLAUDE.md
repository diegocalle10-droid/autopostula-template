# Autopostula: lo que el código no dice

- **Puesta en marcha, en este orden:**
  1. **Entrevista** (`CONFIGURAR.md`): si el usuario pide «configura mi Autopostula», o `inputs/cv.md`, `inputs/puestos.md` o `inputs/ubicaciones.md` no tienen filas. Se hace en la nube (claude.ai/code) o aquí.
  2. **Instalación en el PC** (`INSTALAR.md`): si el usuario lo pide, o si estás en su Windows y `python cli.py doctor` falla. Antes de nada comprueba el stack obligatorio (Git, Python 3.12+ como `python`, Chrome) e instala lo que falte con su permiso.
- **Neon es la única base oficial.** La SQLite (`data/ofertas.sqlite`) es solo un transporte hacia Neon; ambas deben tener lo mismo en las tablas de la captura. Nada nuevo vive solo en SQLite.
- **`inputs/` es la única fuente de parámetros y de textos** (incluido todo lo de Telegram, en `inputs/mensajes/`). El código no lleva términos, países, modalidades, reglas ni textos escritos; si hay que cambiar uno, se cambia ahí.
- **Reglas fijas del sistema (no son parámetros):** solo Easy Apply (`f_AL=true` en el código), solo ofertas abiertas y 3 intentos por CV rechazado (`INTENTOS_MAXIMOS` en `collector/online/pdfs.py` y la vista `ofertas_por_redactar` de `001_neon.sql`: si cambia, cambian los dos).
- **Cada lugar de `inputs/ubicaciones.md` necesita su `geo_id`**: la lista de empleos de LinkedIn ignora el texto de la ubicación y, sin `geo_id`, busca en la de la cuenta. Siempre que se definan o cambien lugares (entrevista o después), el `geo_id` se resuelve con `python cli.py geoids --escribir` en el PC con la sesión iniciada; nunca a mano ni de memoria. Sin él, `run` y `run-continuo` no arrancan.
- **Un solo proceso de peticiones a LinkedIn a la vez** (`data/.lock`). Las pausas de `inputs/lotes.md` nunca bajan de 60 s por petición; ante un 429 no se reintenta.
- **Límites de código:** archivos ≤ 300 líneas y funciones ≤ 40 (`python tools/check_size.py`); pruebas con `python -m unittest discover -s tests`, que usan los datos de ejemplo de `tests/fixtures/` y no los de `inputs/`. La Action «Pruebas» los pasa en cada subida.
- **Nunca** subir `.env`, `data/` (base local y sesión de LinkedIn) ni PDF; la única excepción es el CV en `CV/entrada/` durante la entrevista, que se borra al terminar.

## Dónde va cada cosa

Un dato vive en un solo sitio; los demás lo citan por su nombre (`horas_por_defecto`, `tope_rutina`…), sin copiar su valor. Solo se repite una idea cuando la leen públicos distintos: el README la cuenta a la persona, el guion la ordena a la IA y la guía muestra dónde hacer clic.

| Documento | Lo lee | Lleva | No lleva |
|---|---|---|---|
| `README.md` | La persona usuaria y quien llega al repositorio | Qué es, aviso legal, stack obligatorio, los tres pasos de la puesta en marcha, uso diario, actualizar, problemas; al final, una sección breve para desarrolladores | Pasos de instalación detallados, clics, descripciones de módulos |
| `CLAUDE.md` | La IA que trabaja en el repositorio | Invariantes que el código no dice, a qué guion ir y esta tabla | Pasos, descripciones de módulos |
| `CONFIGURAR.md`, `INSTALAR.md` | La IA que guía al usuario | Instrucciones paso a paso y qué comprobar; enlazan las guías | Clics y capturas (están en `guia/`), valores de parámetros |
| `guia/*.md` | La persona usuaria | Dónde hacer clic en cada servicio, con capturas | Lógica del sistema, comandos |
| `CV/PROMPT_RUTINA.md` | La rutina de la nube (y el bot, secciones 3.1-3.3) | Cómo redactar y registrar los CV | Valores de `inputs/` (los lee de ahí) |
| `CV/PROMPT_MINIMO.md` | La persona, para pegarlo en la rutina | La única frase que lleva la rutina | Reglas |
| `skills-project-bot/` | El bot de gestión | `00` contexto, `01` orquestador (con los disparadores), `F1`-`F7` los pasos de cada función; `LEEME.md`, qué archivo va dónde | Cifras de parámetros |
| `inputs/*.md` | El código y la IA (entrevista, rutina, bot) | Parámetros en tablas y una explicación breve de cada uno | Historia del proyecto, valores repetidos en la prosa |
| `configurar/` | La entrevista | Material que copia (CV de ejemplo, glosarios de idioma) | |
| Docstring de cada módulo | Quien lee el código | Qué hace el módulo | Listas de módulos en otros documentos |
| Migraciones (`*/migrations/*.sql`) | El código | El esquema, la única fuente de tablas y columnas; en `001_neon.sql`, quién escribe cada tabla | |
