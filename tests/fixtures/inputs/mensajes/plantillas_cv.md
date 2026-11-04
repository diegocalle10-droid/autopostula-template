# Mensajes de Telegram: plantillas del CV a medida y de la rutina

Los envía la Action `CV a PDF` (PDF listo, sin CV, rechazo, resumen de la rutina). Incluye las piezas comunes (viñetas, consulta). Formato HTML de Telegram (solo `<b>` y `<code>`); `
` es un salto de línea; `{campo}` lo rellena el código con datos ya escapados. Qué marcadores admite cada plantilla lo fija el código (`collector/config/textos.py`).

## Mensajes

| id | plantilla |
|---|---|
| cv_listo | {emoji} <b>{cabecera}</b>\nID: {job_id}\n{lugar}CV {cv_id} · afinidad {afinidad} %\n{url} |
| sin_cv | {emoji} <b>Sin CV · {cabecera}</b>\nID: {job_id}\nAfinidad {afinidad} % · {motivo}\n{url}\nPara generarlo igualmente: en el Project, «genera el CV para {job_id}» |
| rechazo | {emoji} <b>CV rechazado (intento {intento} de {maximo}) · {cabecera}</b>\nID: {job_id}\nMotivo: {motivo}\n{url}\n{cierre}\n{consulta} |
| rechazo_cierre_final | No se reintenta más: en el Project, «corrige el rechazo de {job_id}» |
| rechazo_cierre_reintento | La rutina lo reescribirá en su próxima ejecución. |
| resumen_rutina | {emoji} <b>CV a medida · {dia}</b>\nRedactados {redactados} ({correcciones} correcciones) · Sin CV {sin_cv} · Quedan por redactar {quedan}{bloque} |
| resumen_quedan | \n\nQuedan por redactar (sin registrar o fuera del tope de {tope}):\n{lista} |
| nada_por_redactar | {emoji} Nada por redactar hoy {dia} |
| rutina_sin_registros | {emoji} <b>La rutina terminó sin registrar nada · {dia}</b>\nQuedan por redactar {quedan}:\n{lista} |
| vineta_oferta | • {job_id} · {cabecera} |
| vinetas_mas | … y {n} más |
| consulta | <code>{sql}</code>\nNeon: {url} |
| sql_rechazo | SELECT * FROM emparejamientos WHERE job_id = '{job_id}'; |
