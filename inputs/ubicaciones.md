# Ubicaciones de búsqueda (parámetro de entrada)

Este archivo es la **única fuente** de los lugares donde se busca. El código lo lee; no tiene listas propias. Lo rellena la entrevista (`CONFIGURAR.md`); no hay ningún lugar por defecto.

Reglas:
- `frase` es el texto exacto que se envía a LinkedIn como ubicación. Puede ser un país (`Spain`), una región (`Canary Islands`, `Latin America`) o una ciudad (`Madrid`). LinkedIn **no siempre reconoce los nombres en español**: usa el nombre en inglés si con el español no salen resultados.
- `tipo` es informativo: `pais`, `region` o `ciudad`.
- `geo_id` es el identificador de LinkedIn del lugar. La lista de empleos ignora el texto de la ubicación: sin `geo_id` aplica la ubicación de tu cuenta y la búsqueda no sirve. No se escribe a mano: lo resuelve `python cli.py geoids --escribir` con la sesión de LinkedIn iniciada (ver `INSTALAR.md`). Mientras no esté resuelto, `-`; la captura no arranca con un lugar sin `geo_id`.
- `pais_esperado` es el país al que pertenece el lugar, escrito como lo muestra LinkedIn en la ubicación de las ofertas (`Spain`, `Mexico`). Se usa cuando una oferta trae una ubicación sin país («Greater Madrid Metropolitan Area»). En una región de varios países, `-`.
- Una oferta solo se acepta si su país está en la tabla **Países aceptados**. Así una búsqueda regional no cuela países que no quieres.
- Una ubicación que no da resultados o es redundante con otra se elimina de la tabla.

## Lugares

| tipo | frase | pais_esperado | geo_id | nota |
|---|---|---|---|---|

## Países aceptados

Una oferta solo se acepta si su país está en esta tabla. Qué se hace con un país excluido, desconocido o con una oferta duplicada se decide en `decisiones.md`.
En una búsqueda con `pais_esperado`, una ubicación sin nombre de país se atribuye a ese país.

| pais | prioridad_detalle |
|---|---|

`prioridad_detalle` (1 = primero) ordena a qué ofertas se les pide antes el detalle (ver `prefiltro.md`).

## Países excluidos

Opcional. Países que aparecen en búsquedas regionales y se sabe que no valen.

| pais | nota |
|---|---|
