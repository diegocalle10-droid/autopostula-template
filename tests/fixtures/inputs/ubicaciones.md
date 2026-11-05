# Ubicaciones de búsqueda (parámetro de entrada)

Este archivo es la **única fuente** de países y regiones. El código lo lee; no tiene listas propias.
Validado con búsquedas reales de la fase 0 (remoto, 30 días, sin palabra clave).

Reglas:
- Una ubicación que falla (0 resultados) o es redundante con otra se **elimina** de la tabla.
- La tabla **Reserva** no la lee el código: son capitales y siglas pendientes de medir en producción.
- `frase` es el texto exacto que se envía a LinkedIn como ubicación. LinkedIn **no reconoce los nombres en español**: se usan los nombres en inglés.
- `geo_id` es el identificador de LinkedIn de la ubicación: la nueva lista de búsqueda ignora el texto de la ubicación y aplica la de la cuenta si no recibe `geoId`. Resuelto con el desplegable de ubicación y validado el 2026-11-05 (el desplegable muestra el país y las tarjetas son de ese país).
- `pais_esperado` es el texto que debe aparecer en la ubicación de los resultados.
- Una oferta solo se acepta si su país está en la tabla **Países aceptados**. Esto deja fuera, por ejemplo, a Brasil cuando una búsqueda regional lo devuelve.

## Países

| tipo | frase | pais_esperado | geo_id | nota |
|---|---|---|---|---|
| pais | Mexico | Mexico | 103323778 |  |
| pais | Guatemala | Guatemala | 100877388 |  |
| pais | Honduras | Honduras | 101937718 |  |
| pais | El Salvador | El Salvador | 106522560 |  |
| pais | Nicaragua | Nicaragua | 105517145 |  |
| pais | Costa Rica | Costa Rica | 101739942 |  |
| pais | Panama | Panama | 100808673 |  |
| pais | Dominican Republic | Dominican Republic | 105057336 |  |
| pais | Puerto Rico | Puerto Rico | 105245958 |  |
| pais | Colombia | Colombia | 100876405 |  |
| pais | Venezuela | Venezuela | 101490751 |  |
| pais | Ecuador | Ecuador | 106373116 |  |
| pais | Peru | Peru | 102927786 |  |
| pais | Bolivia | Bolivia | 104379274 |  |
| pais | Chile | Chile | 104621616 | 9/10 Chile, 1 con "Santiago Metropolitan Area" (el filtro de país debe aceptar áreas metropolitanas) |
| pais | Argentina | Argentina | 100446943 |  |
| pais | Uruguay | Uruguay | 100867946 |  |
| pais | Paraguay | Paraguay | 104065273 |  |
| pais | Equatorial Guinea | Equatorial Guinea | 105141335 | poco volumen esperado |

## Regiones

Solo «Latin America» funciona como región en la nueva lista: «South America» se eliminó el 2026-11-05 porque el desplegable de ubicación no la ofrece. Cobertura de Centroamérica, Caribe y Cono Sur: se logra con los países individuales de la tabla anterior.

| tipo | frase | pais_esperado | geo_id | nota |
|---|---|---|---|---|
| region | Latin America | - | 91000011 | Mezcla Brasil, Uruguay, Puerto Rico, México y otros: aplicar filtro de países aceptados |

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
| República Dominicana | 1 |
| Guinea Ecuatorial | 1 |
| América Latina | 1 |

Las tres últimas son los nombres en español con que la lista de LinkedIn muestra esos lugares (los demás coinciden al quitar tildes).

`prioridad_detalle` (1 = primero) ordena a qué ofertas se les pide antes el detalle (ver `prefiltro.md`). 

## Países excluidos

Países que aparecen en búsquedas regionales y se sabe que no valen. La lista crece con lo que se vaya viendo en `revisar`.

| pais | nota |
|---|---|
| Brazil | No es hispanohablante; sale en "Latin America" |
| Brasil | Variante en español |
| Spain | Retirada del todo por decisión de Diego (2026-10-31): no se busca ni se acepta |
| España | Variante en español |
