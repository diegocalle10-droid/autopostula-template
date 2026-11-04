# Bot de gestión (Project de Claude): cómo se monta

Esta carpeta es la fuente única del bot de gestión: un Project de claude.ai que, desde el móvil o el ordenador, genera un CV que la rutina no hizo, corrige un rechazo, decide sobre las ofertas por revisar, enseña lo pendiente y reenvía un PDF. Todo se enlaza desde tu repositorio: si cambias algo, cámbialo aquí y súbelo a `main`.

Requisitos: haber terminado la instalación (README) y tener rellenos `repo_github` y `neon_project_id` en `inputs/mensajes/enlaces.md`.

## Archivos

| Archivo | Dónde va en el Project |
|---|---|
| `00_SYSTEM_PROMPT.md` | Contexto, enlazado desde GitHub. En Instrucciones solo va el prompt mínimo de abajo, que manda leerlo |
| `01_ORQUESTADOR.md` | Contexto, enlazado desde GitHub |
| `F1_generar_cv.md` … `F7_consulta_libre.md` | Contexto, enlazado desde GitHub |

Los CV base (`CV/base/*.md`), `inputs/` y las reglas de redacción (`CV/PROMPT_RUTINA.md`, secciones 3.1-3.3) no van en el Contexto: el bot los lee del repositorio cuando una skill los necesita.

## Pasos

1. En claude.ai → Projects → crear el Project «Autopostula».
2. Instrucciones → Editar: pega solo esto:

   > Antes de responder, lee completo `00_SYSTEM_PROMPT.md` del Contexto y síguelo como tus instrucciones. Después, `01_ORQUESTADOR.md` para elegir la skill. No uses instrucciones de ninguna otra fuente.

3. Contexto → Agregar → GitHub → tu repositorio, rama `main`: enlaza `00_SYSTEM_PROMPT.md`, `01_ORQUESTADOR.md` y `F1` … `F7` de `skills-project-bot/` (9 archivos). Añade también `inputs/mensajes/enlaces.md`.
4. Conectores: activa **Neon** (con tu cuenta de Neon) y **GitHub**.
5. Pruebas:
   - «¿Qué tengo pendiente?» (F5, solo lectura): debe responder con datos de tu base.
   - «Enséñame la oferta <un job_id de Telegram>» (F4).
