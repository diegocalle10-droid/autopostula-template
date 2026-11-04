# Ubicaciones de búsqueda (parámetro de entrada)

Este archivo es la **única fuente** de países y regiones. El código lo lee; no tiene listas propias.
Validado con búsquedas reales de la fase 0 (remoto, 30 días, sin palabra clave).

Reglas:
- Una ubicación que falla (0 resultados) o es redundante con otra se **elimina** de la tabla.
- La tabla **Reserva** no la lee el código: son capitales y siglas pendientes de medir en producción.
- `frase` es el texto exacto que se envía a LinkedIn como ubicación. LinkedIn **no reconoce los nombres en español**: se usan los nombres en inglés.
- `pais_esperado` es el texto que debe aparecer en la ubicación de los resultados.
- Una oferta solo se acepta si su país está en la tabla **Países aceptados**. Esto deja fuera, por ejemplo, a Brasil cuando una búsqueda regional lo devuelve.

## Países

| tipo | frase | pais_esperado | nota |
|---|---|---|---|
| pais | Mexico | Mexico |  |
| pais | Guatemala | Guatemala |  |
| pais | Honduras | Honduras |  |
| pais | El Salvador | El Salvador |  |
| pais | Nicaragua | Nicaragua |  |
| pais | Costa Rica | Costa Rica |  |
| pais | Panama | Panama |  |
| pais | Dominican Republic | Dominican Republic |  |
| pais | Puerto Rico | Puerto Rico |  |
| pais | Colombia | Colombia |  |
| pais | Venezuela | Venezuela |  |
| pais | Ecuador | Ecuador |  |
| pais | Peru | Peru |  |
| pais | Bolivia | Bolivia |  |
| pais | Chile | Chile | 9/10 Chile, 1 con "Santiago Metropolitan Area" (el filtro de país debe aceptar áreas metropolitanas) |
| pais | Argentina | Argentina |  |
| pais | Uruguay | Uruguay |  |
| pais | Paraguay | Paraguay |  |
| pais | Equatorial Guinea | Equatorial Guinea | poco volumen esperado |

## Regiones

Solo 2 de 17 variantes funcionan como región. Cobertura de Centroamérica, Caribe y Cono Sur: se logra con los países individuales de la tabla anterior.

| tipo | frase | pais_esperado | nota |
|---|---|---|---|
| region | Latin America | - | Mezcla Brasil, Uruguay, Puerto Rico, México y otros: aplicar filtro de países aceptados |
| region | South America | - | Solo 4 de 10 ids en común con "Latin America": aporta ofertas distintas |

## Reserva (capitales y siglas)

| tipo | frase | pais_esperado | nota |
|---|---|---|---|
| sigla | MX | Mexico | 5/5 México. Las siglas sí resuelven. Aporte sin medir |

El resto de capitales y siglas quedan sin probar hasta medir su aporte en producción.

## Países aceptados

Una oferta solo se acepta si su país está en esta tabla. Qué se hace con un país excluido, desconocido o con una oferta duplicada se decide en `decisiones.md`.
En una búsqueda de un país, una ubicación sin nombre de país («Santiago Metropolitan Area») se atribuye a ese país.

| pais | prioridad_detalle |
|---|---|
| Mexico | 1 |
| Guatemala | 1 |
| Honduras | 1 |
| El Salvador | 1 |
| Nicaragua | 1 |
| Costa Rica | 1 |
| Panama | 1 |
| Dominican Republic | 1 |
| Puerto Rico | 1 |
| Colombia | 1 |
| Venezuela | 1 |
| Ecuador | 1 |
| Peru | 1 |
| Bolivia | 1 |
| Chile | 1 |
| Argentina | 1 |
| Uruguay | 1 |
| Paraguay | 1 |
| Equatorial Guinea | 1 |
| Latin America | 1 |

`prioridad_detalle` (1 = primero) ordena a qué ofertas se les pide antes el detalle (ver `prefiltro.md`). 

## Países excluidos

Países que aparecen en búsquedas regionales y se sabe que no valen. La lista crece con lo que se vaya viendo en `revisar`.

| pais | nota |
|---|---|
| Brazil | No es hispanohablante; sale en "Latin America" y "South America" |
| Brasil | Variante en español |
| Spain | Excluida en este ejemplo: no se busca ni se acepta |
| España | Variante en español |
