# Autopostula: lo que el código no dice

- **Puesta en marcha, en este orden:**
  1. **Entrevista** (`CONFIGURAR.md`): si el usuario pide «configura mi Autopostula», o `inputs/cv.md`, `inputs/puestos.md` o `inputs/ubicaciones.md` no tienen filas. Se hace en la nube (claude.ai/code) o aquí.
  2. **Instalación en el PC** (`INSTALAR.md`): si el usuario lo pide, o si estás en su Windows y `python cli.py doctor` falla. Antes de nada comprueba el stack obligatorio (Git, Python 3.12+ como `python`, Chrome) e instala lo que falte con su permiso.
  Cada guion es la única fuente de sus pasos: no los copies en otro sitio.
- **Neon es la única base oficial.** La SQLite (`data/ofertas.sqlite`) es solo un transporte hacia Neon; ambas deben tener lo mismo en las tablas de la captura. Nada nuevo vive solo en SQLite.
- **`inputs/` es la única fuente de parámetros y de textos** (incluido todo lo de Telegram, en `inputs/mensajes/`). El código no lleva términos, países, modalidades, reglas ni textos escritos; si hay que cambiar uno, se cambia ahí.
- **Las instrucciones de la rutina de CV viven solo en `CV/PROMPT_RUTINA.md`.** La rutina de la nube lleva el prompt mínimo de `CV/PROMPT_MINIMO.md`, que lo lee del repositorio clonado; nunca se copian reglas en la rutina.
- **Reglas fijas del sistema (no son parámetros):** solo Easy Apply (`f_AL=true` en el código) y solo ofertas abiertas.
- **Un solo proceso de peticiones a LinkedIn a la vez** (`data/.lock`); 60-90 s por petición; ante un 429 no se reintenta.
- **Límites de código:** archivos ≤ 300 líneas y funciones ≤ 40 (`python tools/check_size.py`); pruebas con `python -m unittest discover -s tests`, que usan los datos de ejemplo de `tests/fixtures/` y no los de `inputs/`. La Action «Pruebas» los pasa en cada subida.
- **Nunca** subir `.env`, `data/` (base local y sesión de LinkedIn) ni PDF; la única excepción es el CV en `CV/entrada/` durante la entrevista, que se borra al terminar.
