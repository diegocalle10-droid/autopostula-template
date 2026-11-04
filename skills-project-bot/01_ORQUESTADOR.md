# Orquestador: qué skill usar en cada caso

Lee este mapa antes de actuar. Elige **una** skill y lee solo esa. Los disparadores son ejemplos, no una lista cerrada: el usuario habla en lenguaje natural, con sinónimos, faltas, mayúsculas y frases a medias. Decide por la **intención** y traduce sus palabras con el glosario.

## Cómo entender al usuario

1. **Traduce sus palabras a valores de la base** con el glosario. Da igual cómo lo escriba («Revisar», «por revisar», «a revisión», «las dudosas»): la base guarda `revisar`.
2. **Identifica la acción**: ¿quiere *ver o contar* (lectura) o *cambiar* algo (escritura)?
3. **Elige la skill** con el mapa. Si es lectura y ninguna skill la cubre exactamente, usa `F7_consulta_libre.md`, nunca SQL improvisado fuera de una skill.
4. **Si dudas entre dos significados**, elige el más probable, dilo en una línea («Entiendo que quieres las ofertas en estado revisar») y sigue; si el error tendría consecuencias (una escritura), pregunta antes.

## Glosario: lo que dice el usuario → lo que hay en la base

| El usuario dice (o algo parecido) | Significa | En la base |
|---|---|---|
| por revisar, a revisar, en revisión, revisión, dudosas, las que hay que mirar | ofertas que esperan su decisión | `ofertas.estado = 'revisar'` |
| aptas, aprobadas, válidas, buenas, las que valen | ofertas que pasaron todas las reglas | `ofertas.estado = 'apta'` |
| descartadas, desechadas, eliminadas, las que no valen | ofertas descartadas (motivo en `motivo_descarte`) | `ofertas.estado = 'descartada'` |
| pendientes **de detalle**, sin detalle, en cola, sin procesar, que no se han mirado | ofertas cuyo detalle aún no se pidió | `ofertas.estado = 'pendiente'` |
| pendiente(s) a secas, qué tengo pendiente, qué falta | lo que requiere atención en todo el sistema | `F5` (incluye las pendientes de detalle) |
| sin CV, no llegó al umbral, sin currículum | ningún CV base llegaba al umbral (`umbral_afinidad` de `inputs/cv.md`) | `emparejamientos.estado = 'sin_cv'` |
| CV **rechazado**, falló la validación, lo tumbaron | el CV no pasó la validación | `emparejamientos.estado = 'rechazada'` |
| rechazo agotado, sin más intentos | agotó los intentos (`intentos_maximos` de `inputs/mensajes/parametros.md`) | `estado = 'rechazada' AND intentos >= 3` |
| enviados, me llegaron, los que tengo en Telegram | PDF enviado | `emparejamientos.notificado_en IS NOT NULL` |
| CV, currículum, curriculum, hoja de vida, PDF | el CV a medida | `emparejamientos` (`cv_md`) |
| oferta, vacante, puesto, anuncio, trabajo, ID, número | una fila de `ofertas` | `ofertas.job_id` |
| categoría, estado, tipo, situación | el estado de una oferta o de su CV | `ofertas.estado` / `emparejamientos.estado` |

Ojo: «rechazada» aplicado a una **oferta** casi siempre significa `descartada`; aplicado a un **CV**, `rechazada`.

## Mapa rápido

| Skill | Para qué | Intención típica | Escribe en la base |
|---|---|---|---|
| `F1_generar_cv.md` | Redactar un CV para una oferta concreta, sin umbral de afinidad | «genera / hazme / quiero el CV de…» | Sí |
| `F2_marcar_revision.md` | Decidir sobre ofertas: aptas o descartadas | «márcala como apta / descártala» | Sí |
| `F3_corregir_rechazo.md` | Arreglar un CV que la validación rechazó | «corrige / arregla el rechazo de…» | Sí |
| `F4_ver_oferta.md` | Ver todo sobre una oferta | «enséñame / cómo está / qué pasó con…» | No |
| `F5_pendientes.md` | Ver lo pendiente del sistema | «qué tengo pendiente / qué hay por revisar» | No |
| `F6_reenviar_pdf.md` | Volver a recibir un PDF ya generado | «reenvíame / no me llegó el PDF de…» | Sí |
| `F7_consulta_libre.md` | Cualquier otra pregunta de lectura: listar, contar, agrupar, buscar | «muéstrame / cuántas / qué empresas / por país…» | No |

## Reglas de desempate

1. **Generar vs. corregir**: si la oferta tiene un emparejamiento en estado `rechazada`, es `F3` aunque el usuario diga «genera». Si no tiene emparejamiento, o está en `sin_cv`, es `F1`. Si ya está `validada`, pregunta si quiere un CV nuevo (`F1`) o solo el PDF otra vez (`F6`).
2. **Marcar apta y generar a la vez** («márcala apta y hazle el CV»): primero `F2`, después `F1` sobre el mismo id.
3. **«Revisa X»** es ambiguo: si X es una oferta concreta, quiere verla para decidir (`F4`); si pide ver *las* ofertas por revisar, es una lista (`F5` si quiere el panorama, `F7` si solo quiere esa lista).
4. **Lista o recuento de un solo estado** («muéstrame las que están por revisar», «tabla de las pendientes», «cuántas aptas hay»): `F7`. Panorama general («qué tengo pendiente», «resumen»): `F5`.
5. **Varias peticiones en un mensaje**: hazlas en orden, una skill cada vez, y resume al final.
6. **Nada encaja**: pregunta en una línea. No escribas en la base sin una skill que lo cubra.

## Disparadores por skill

### F1 · Generar CV
- «Genera el CV para 4012345678»
- «Hazme el CV de la oferta 4012345678 aunque no llegue al umbral»
- «Quiero candidatarme a 4012345678, prepárame el CV»
- «Esta sin CV me interesa: 4012345678»
- «Redacta un CV para Acme, el ID es 4012345678»
- «Usa el CV de data analytics para la 4012345678»
- «Vuelve a hacer el CV de 4012345678 desde cero»
- «Genera CV para estas: 4012…, 4013…, 4014…»

### F2 · Marcar revisión
- «Marca 4012345678 como apta»
- «Descarta la 4012345678, no me interesa»
- «4012… apta, 4013… descartada, 4014… apta»
- «Esta que estaba a revisar sí me vale: 4012345678»
- «La de modalidad híbrida, 4012345678, descártala»
- «Pasa a apta todas las de idioma aceptable»
- «Recupera la 4012345678, la descartaste pero sí me interesa»
- «Ya revisé las 12: aptas 4012… y 4013…, el resto descartadas»

### F3 · Corregir rechazo
- «Corrige el rechazo de 4012345678»
- «Arregla el CV de 4012345678, lo rechazaron por la raya larga»
- «El CV de 4012345678 se pasa de páginas, recórtalo»
- «¿Por qué rechazaron 4012345678? Arréglalo»
- «Se agotaron los intentos de 4012345678, corrígelo tú»
- «Repara los CV rechazados»
- «4012345678 tiene un fallo en las fechas, corrígelo»

### F4 · Ver oferta
- «Enséñame la 4012345678»
- «¿Cómo está la 4012345678?»
- «¿Qué pasó con el CV de 4012345678?»
- «¿Por qué 4012345678 está a revisar?»
- «Pásame la descripción de 4012345678»
- «¿Qué CV se eligió para 4012345678 y con qué afinidad?»
- «Muéstrame el CV que se redactó para 4012345678»
- «¿Se envió ya el PDF de 4012345678?»

### F5 · Pendientes
- «¿Qué tengo pendiente?»
- «¿Qué falta por hacer?»
- «¿Cómo va todo?»
- «¿Qué hay por revisar?»
- «Lista las ofertas sin CV»
- «¿Cuántos CV se enviaron hoy?»
- «¿Hay rechazos agotados?»
- «Resumen del estado del sistema»
- «¿Qué va a redactar la rutina la próxima vez?»
- «¿Cuántas aptas hay sin CV?»

### F7 · Consulta libre (solo lectura)
- «Muéstrame todas las ofertas que estén por revisar»
- «Hazme una tabla de las pendientes»
- «¿Cuántas vacantes hay en cada estado?»
- «¿Por qué motivos se descartaron?» / «agrupa las descartadas por motivo»
- «¿Qué empresas tienen ofertas aptas?»
- «Ofertas de Guatemala»
- «Lo que entró esta semana»
- «Busca ofertas de Power BI»

### F6 · Reenviar PDF
- «Reenvíame el PDF de 4012345678»
- «No me llegó el CV de 4012345678 a Telegram»
- «Mándame otra vez el PDF de 4012345678»
- «Borré el mensaje de 4012345678, reenvíalo»
- «Regenera el PDF de 4012345678 sin cambiar el texto»
- «Vuelve a mandarme los PDF de 4012… y 4013…»
