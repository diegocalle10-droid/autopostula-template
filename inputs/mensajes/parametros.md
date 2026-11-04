# Mensajes de Telegram: parámetros

Cómo se formatean y se acortan los mensajes. Forma parte del conjunto `inputs/mensajes/` (ver `plantillas_*.md` para los textos).

## Ajustes

| clave | valor | nota |
|---|---|---|
| zona_horaria | Europe/Madrid | Zona de las fechas y horas de los mensajes |
| formato_fecha | %d/%m/%Y | |
| formato_hora | %d/%m/%Y %H:%M | |
| formato_hora_corta | %H:%M | |
| presupuesto_vinetas | 3000 | Caracteres para listas: el mensaje entero cabe en los 4.096 de Telegram |
| prefijo_pdf | CV - | Nombre del PDF que llega por Telegram: este prefijo, un espacio y el título de la vacante |
| sin_empresa | Sin empresa | Cuando la oferta no trae empresa |
| sin_motivo | sin motivo | Cuando una oferta por revisar no trae motivo |
