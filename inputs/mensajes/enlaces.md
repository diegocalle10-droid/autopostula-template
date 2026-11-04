# Mensajes de Telegram: enlaces y horas fijas

Datos fijos de tu instalación que usan los mensajes, la rutina y el bot. Los rellena la entrevista (`CONFIGURAR.md`) y la guía de instalación; mientras digan `PENDIENTE`, `python cli.py doctor` lo avisa.

## Ajustes

| clave | valor | nota |
|---|---|---|
| repo_github | PENDIENTE | Tu repositorio privado, como `usuario/repo`. La rutina lanza aquí la Action `CV a PDF` |
| neon_project_id | PENDIENTE | Id del proyecto de Neon (Settings → General). Lo usan la rutina y el bot con el conector de Neon |
| url_consola_neon | PENDIENTE | Editor SQL de tu proyecto: `https://console.neon.tech/app/projects/<neon_project_id>/sql-editor` |
| url_rutina | PENDIENTE | Enlace de tu rutina de CV (opcional; ver `guia/rutina.md`): se puede lanzar a mano desde aquí |
| hora_rutina | PENDIENTE | Hora a la que se dispara sola la rutina, con su zona (p. ej. `06:00 (hora de Madrid)`) |
