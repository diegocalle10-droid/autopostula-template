# INSTALAR — Puesta en marcha en tu PC

> Única fuente del guion de instalación. Lo sigue Claude Code en tu ordenador (app de escritorio de Claude → pestaña **Code**) después de la entrevista (`CONFIGURAR.md`). Deja instalada la captura, conectados Neon, Telegram, GitHub y la rutina, y termina activando el envío diario cuando todo funciona.

## 0. Reglas para Claude

- Habla en español, claro y sin tecnicismos. Un paso a la vez; comprueba cada uno antes de pasar al siguiente. Si el usuario vuelve otro día, empieza por `python cli.py doctor` para saber dónde se quedó.
- **Secretos:** nunca le pidas que pegue en el chat una cadena de conexión, un token ni una contraseña, y nunca los imprimas. Para escribirlos, abre el `.env` con `notepad .env` y que los pegue él. El *Project ID* de Neon, la URL de la rutina y el chat id de Telegram no son secretos.
- **Pide permiso** antes de instalar programas o cambiar ajustes de Windows, y di qué vas a hacer.
- Cuando un paso tenga guía con capturas (`guia/<tema>.md`), dale el enlace.
- Escribe solo en `.env`, `inputs/mensajes/enlaces.md` y, en la activación, `.github/workflows/cv-pdf.yml`. Cada cambio en el repositorio, commit y `git push` a `main` en el momento: la rutina y el bot leen GitHub, no este PC.

## 1. Programas obligatorios

Comprueba cada uno; si falta, ofrécete a instalarlo con `winget` y, tras instalar, abre una consola nueva para que el PATH se actualice.

| Programa | Comprobación | Instalación |
|---|---|---|
| Git | `git --version` | `winget install --id Git.Git -e` |
| Python 3.12 o superior, como `python` | `python --version` (no basta con `py`) | `winget install --id Python.Python.3.13 -e` |
| Google Chrome | existe `C:\Program Files\Google\Chrome\Application\chrome.exe` | `winget install --id Google.Chrome -e` |
| GitHub CLI (recomendado) | `gh --version` y `gh auth status` | `winget install --id GitHub.cli -e`; luego el usuario ejecuta `gh auth login` |

## 2. El repositorio

1. Si la carpeta aún no tiene el repositorio, clónalo (`git clone https://github.com/<repo_github>.git .`).
2. **Enlace con la plantilla**, una sola vez, para que las actualizaciones futuras no choquen. Si `git merge-base HEAD plantilla/main` ya responde, está hecho:
   ```
   git remote add plantilla https://github.com/diegocalle10-droid/autopostula-template.git
   git fetch plantilla
   git merge plantilla/main --allow-unrelated-histories -s ours -m "Enlace con la plantilla"
   git push
   ```
   No cambia ningún archivo: solo registra que el repositorio viene de la plantilla. Desde aquí, actualizar es `git pull plantilla main`, y solo choca lo que cambiaron los dos.
3. `python -m pip install -r requirements-captura.txt`.
4. `copy .env.example .env`.

## 3. Neon (la base de datos)

1. Guía: `guia/neon.md`. El usuario crea la cuenta y el proyecto, y copia la cadena de conexión de **Connect**.
2. `notepad .env` → la pega en `NEON_DATABASE_URL` y guarda.
3. Pídele el *Project ID* (dónde está: misma guía). Escríbelo en `inputs/mensajes/enlaces.md`: `neon_project_id` y `url_consola_neon` (`https://console.neon.tech/app/projects/<id>/sql-editor`). Commit y push.

## 4. Telegram

1. Guía: `guia/telegram.md`. Con @BotFather crea el bot y copia el token.
2. `notepad .env` → lo pega en `TELEGRAM_BOT_TOKEN`.
3. Que escriba cualquier mensaje a su bot. Ejecuta `python cli.py telegram-chat-id` y escribe el número en `TELEGRAM_CHAT_ID` del `.env`.

## 5. Base, agenda y LinkedIn

1. `python cli.py instalar`. Debe terminar sin fallos salvo los avisos de la sesión de LinkedIn y de los enlaces aún pendientes.
2. `python cli.py sesion`: se abre Chrome. El usuario inicia sesión en LinkedIn con email y contraseña (recomendado: una cuenta secundaria, con la interfaz en español o inglés). Si LinkedIn pide un código, lo introduce en la misma ventana.

## 6. Que el PC no se duerma

La captura dura varias horas de noche: si Windows suspende o hiberna el PC, se corta sin avisar.

1. Comprueba: `powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE` y `powercfg /query SCHEME_CURRENT SUB_SLEEP HIBERNATEIDLE`. Los índices de corriente alterna (con cargador) y continua (batería) están en segundos en hexadecimal; `0x00000000` es «nunca».
2. Si alguno es menor que `horas_por_defecto` (`inputs/lotes.md`) más una hora, explícaselo y ofrece una de dos: que lo cambie él (guía `guia/energia-windows.md`), o hacerlo tú con su permiso: `powercfg /change standby-timeout-ac 0`, `standby-timeout-dc 0`, `hibernate-timeout-ac 0` y `hibernate-timeout-dc 0`. La pantalla sí puede apagarse. Al terminar la captura el PC se apaga solo, así que no se queda encendido.
3. En un portátil: enchufado y, si quiere cerrar la tapa, que al cerrarla no haga nada (misma guía).
4. Recomienda que las **horas activas** de Windows Update cubran la noche, para que no reinicie a mitad (misma guía).

## 7. Secretos en GitHub

Con `gh` autenticado: `gh secret set -f .env` (sube `NEON_DATABASE_URL`, `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` sin mostrarlos). Comprueba con `gh secret list`. Sin `gh`, los sube él: guía `guia/github.md`, sección «Secretos».

## 8. La rutina de CV

1. Token de GitHub (guía `guia/github.md`, sección «Token»). Lo guarda él; no lo pegues en el chat.
2. Conector de Neon como conector personalizado de Claude (guía `guia/conector-neon.md`).
3. Rutina, en Programadas de la app de escritorio (guía `guia/rutina.md`): su repositorio, las instrucciones de `CV/PROMPT_MINIMO.md`, disparo diario a su `hora_rutina`, el conector de Neon y la variable de entorno `GITHUB_TOKEN_AUTOPOSTULA` con el token. Repásalo con él antes de guardarla.
4. Pídele el enlace de la rutina (opcional: la guía explica cómo conseguirlo) y escríbelo en `url_rutina` de `inputs/mensajes/enlaces.md`. Si no lo encuentra, déjalo en `PENDIENTE`: todo funciona igual. Commit y push.

## 9. Bot de gestión (opcional)

Si lo quiere: `skills-project-bot/LEEME.md` y guía `guia/bot.md`.

## 10. Ronda de comprobación y activación

Solo cuando todo lo anterior está hecho. Si algo falla, vuelve al paso que corresponda.

1. `python cli.py doctor`: todo `OK` (el único `PENDIENTE` que se admite es `url_rutina`).
2. `python cli.py online-estado`: conecta con Neon.
3. La Action: `gh workflow run cv-pdf.yml -f fuente=manual` y `gh run watch`. Debe terminar en verde (sin `gh`: Actions → «CV a PDF» → Run workflow).
4. La rutina: que la lance a mano una vez desde Programadas (botón de ejecutar ahora). Debe terminar diciendo el código de la Action (`204`), y en `gh run list` aparece una ejecución nueva de «CV a PDF».
5. **Activación:** añade el cron de seguridad a `.github/workflows/cv-pdf.yml`, una vez al día a las 12:00 de su `zona_horaria` convertidas a UTC (calcúlalo con Python y `zoneinfo`), justo debajo del bloque `workflow_dispatch`:
   ```
     schedule:
       - cron: "M H * * *"
   ```
   Commit («Activación: envío diario») y push.
6. Despídete con lo esencial: esta noche, doble clic en `iniciar.bat`, Intro (o las horas que quiera) y a dormir; el PC se apaga solo al terminar (pasados `apagar_tras_captura_min` minutos), y a su `hora_rutina` llegan los CV a Telegram.
