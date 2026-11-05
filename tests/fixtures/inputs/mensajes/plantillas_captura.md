# Mensajes de Telegram: plantillas de la captura

Los envía el PC al terminar `run-continuo` o `detail`, y el protocolo de sesión de LinkedIn: resumen, fin con enlace a la rutina y apagado, alertas, avisos de sesión y estados de la subida a Neon. Mismas reglas de formato que `plantillas_cv.md`.

## Mensajes

| id | plantilla |
|---|---|
| captura | {emoji} <b>Captura terminada · {dia}</b>\nMotivo: {motivo}\nPeticiones {peticiones} (búsquedas {busquedas}, detalles {detalles})\nOfertas nuevas {nuevas} · aptas {aptas}, revisar {revisar}, descartadas {descartadas}\nSubida a Neon: {subida}{revisar_bloque}{cierre} |
| tanda_detalles | {emoji} <b>Tanda de detalles · {dia}</b>\nEvaluadas {procesadas} (aptas {aptas}, revisar {revisar}, descartadas {descartadas}){detenida}\nSubida a Neon: {subida}{revisar_bloque} |
| tanda_detenida | \nDetenida: {motivo} |
| revisar_bloque | \n\n{n} ofertas por revisar ({resumen}):\n{lista}\n{consulta} |
| revisar_vineta | • {job_id} · {cabecera} · {motivo} |
| fin_captura_rutina | \n\nRutina de CV: lánzala ahora desde {url} o se dispara sola a las {hora}. |
| fin_captura_rutina_sin_enlace | \n\nRutina de CV: se dispara sola a las {hora}. |
| fin_captura_apagado | \nEl PC se apaga a las {hora}. Para cancelarlo: shutdown /a |
| aviso_linkedin | {emoji} LinkedIn: {texto} |
| linkedin_verificacion | pidió una verificación al iniciar ({url}). Se para. |
| linkedin_sesion_caducada | la sesión caducó o no existe: inicia sesión en la ventana de Chrome con email y contraseña de LinkedIn (no con Google). |
| alerta_captura | {emoji} <b>Captura: {titulo}</b>\nHora: {cuando}\n{datos} |
| alerta_titulo_parada_total | parada total |
| alerta_titulo_sospecha | parada hasta reanudar |
| alerta_sospecha | Las búsquedas de control tampoco trajeron lista: puede que LinkedIn haya cambiado la página, que la sesión haya caducado o que haya un bloqueo. La próxima captura lo comprueba con una búsqueda y, si funciona, sigue sola. Si lo arreglas antes: python cli.py reanudar |
| alerta_titulo_limite | límite de LinkedIn (429) |
| alerta_titulo_detenida | detenida antes de tiempo |
| alerta_titulo_subida | subida a Neon fallida |
| alerta_titulo_tanda | tanda de detalles detenida |
| alerta_titulo_ctrl_c | detenida a mano (Ctrl+C) |
| alerta_titulo_error | error inesperado ({tipo}) |
| alerta_motivo | Motivo: {motivo} |
| alerta_pausa | Pausa hasta: {hasta} |
| alerta_subida | Subida: {subida} |
| alerta_apagado | El PC se apaga a las {hora}. Para cancelarlo: shutdown /a |
| alerta_reintento | Se reintenta al arrancar la próxima captura. |
| subida_sin_cambios | sin cambios |
| subida_completa | completa |
| subida_no_configurada | no configurada (falta {variable}) |
| subida_fallida | fallida tras 3 intentos ({n} filas en cola) |
