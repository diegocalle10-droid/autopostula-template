# Decisiones sobre las ofertas (parámetro de entrada)

Qué estado recibe una oferta en cada caso. El sistema fija **cuándo** se cumple cada condición (vocabulario cerrado, tablas «Condiciones» y «Situaciones»); tú decides **qué estado y qué motivo** le corresponden.

Estados: `apta`, `revisar`, `descartada`. `pendiente` es interno: una oferta que aún espera su detalle.

## Reglas de ingreso

Se aplican al guardar una oferta nueva, antes de pedir su detalle. En el motivo, `{pais}` y `{original}` se sustituyen por el país de la oferta y por el id de la oferta de la que es duplicada.

| situacion | accion | motivo |
|---|---|---|
| pais_excluido | descartar | pais_excluido:{pais} |
| duplicada | descartar | duplicada_de:{original} |
| pais_desconocido | esperar | pais_desconocido |

Acciones: `descartar` (queda descartada con el motivo), `esperar` (no se pide su detalle hasta que el país se confirme) y `evaluar` (se pide el detalle y la regla `pais_desconocido` de abajo decide). Solo `pais_desconocido` admite las tres; las otras dos situaciones son siempre `descartar`.

## Situaciones

| situacion | se da cuando |
|---|---|
| pais_excluido | El país de la oferta está en «Países excluidos» de `ubicaciones.md` |
| duplicada | Otra oferta tiene la misma huella (empresa, título y ubicación) dentro de `huella_dias` |
| pais_desconocido | La ubicación no se reconoce como país aceptado ni excluido |

## Reglas de decisión

Se evalúan de arriba abajo con el detalle ya leído; gana la primera que se cumple. Deben existir las reglas `cerrada` y `detalle_ilegible`, y la última tiene que ser `siempre`. Una regla `descartada` exige motivo. En el motivo, `{modalidad}` se sustituye por el nombre de la modalidad de la oferta.

| condicion | estado | motivo |
|---|---|---|
| cerrada | descartada | cerrada |
| detalle_ilegible | descartada | detalle_ilegible |
| modalidad_no_aceptada | descartada | modalidad:{modalidad} |
| nivel_exigente | descartada | ingles_exigente |
| nivel_dudoso | revisar | ingles_dudoso |
| contenido_vigilado_titulo_no | revisar | contenido_en_titulo_no_en |
| contenido_vigilado_nivel_aceptable | revisar | anuncio_en_ingles_con_ingles_aceptable |
| contenido_vigilado | descartada | idioma_en_sin_glosario |
| pais_desconocido | revisar | pais_desconocido |
| siempre | apta | |

## Condiciones

«Idioma vigilado» es el idioma cuyo nivel se exige, definido en `idioma.md`.

| condicion | se cumple cuando |
|---|---|
| cerrada | La oferta ya no está activa |
| detalle_ilegible | Su detalle llegó sin contenido `fallos_por_oferta_para_descartar` veces (`lotes.md`); se aplica sin evaluar la oferta, en cualquier posición |
| modalidad_no_aceptada | LinkedIn rotula la oferta con una modalidad que no es la aceptada |
| nivel_exigente | La descripción exige un nivel alto del idioma vigilado |
| nivel_dudoso | Hay señales de nivel aceptable y exigente a la vez |
| contenido_vigilado_titulo_no | La descripción está en el idioma vigilado y el título no |
| contenido_vigilado_nivel_aceptable | La descripción está en el idioma vigilado y el nivel exigido es aceptable |
| contenido_vigilado | La descripción está en el idioma vigilado |
| pais_desconocido | El país de la oferta no se pudo confirmar |
| siempre | Siempre |
