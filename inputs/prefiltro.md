# Prefiltro de detalle (parámetro de entrada)

El detalle es la petición más escasa (una por oferta) y la que decide si se postula. Antes de pedirlo, el título de cada oferta se puntúa con las **familias del título**. Si alcanza `puntuacion_minima`, se pide su detalle y las reglas de `decisiones.md` deciden con la descripción completa (idioma, modalidad…). Si no la alcanza, la oferta queda **descartada** con el motivo `titulo_fuera_de_perfil:<familia>` (la familia negativa de más peso, o `sin_familia` si no aparece ninguna).

El filtro se aplica al entrar cada oferta y, al arrancar `run-continuo`, `detail` o `plan`, a las que sigan pendientes de detalle (por ejemplo, si cambias esta tabla).

Una oferta es **elegible** para el detalle si cumple todo:
1. Su país es uno de **Países aceptados** (`ubicaciones.md`) y está confirmado, salvo que la regla de ingreso `pais_desconocido` de `decisiones.md` sea `evaluar`.
2. Su título alcanza `puntuacion_minima`.
3. No es duplicada ni de un país excluido (eso ya se filtra al recolectar).

Las elegibles se ordenan según la tabla **Orden del detalle**.

## Reglas

| clave | valor | nota |
|---|---|---|
| puntuacion_minima | 1 | Puntos mínimos del título para pedir su detalle |
| prioridad_pais_por_defecto | 1 | Prioridad de un país aceptado sin valor en `ubicaciones.md` |

## Orden del detalle

Criterios en orden de importancia; el primero manda y los siguientes desempatan. Criterios disponibles: `prioridad_pais` (1 = primero, se define en `ubicaciones.md`), `puntos` (puntuación del título) y `recencia` (fecha de publicación). `asc` pone primero el valor menor; `desc`, el mayor.

| criterio | sentido |
|---|---|
| prioridad_pais | asc |
| puntos | desc |
| recencia | desc |

## Familias del título

Cada familia que aparece en el título suma su `peso` **una sola vez**, aunque coincidan varias de sus raíces; la suma es la puntuación. Peso positivo: acerca el título al perfil. Negativo: lo aleja (un título de marketing con «analytics» no pasa).

Cómo se escriben las `raices` (separadas por comas; se comparan sin mayúsculas ni acentos, con los signos de puntuación como espacios):
- `dato*` con asterisco: cualquier palabra que **empiece** así (datos, dato). Cubre plurales, género y variantes sin escribirlas.
- `bi` sin asterisco: la palabra o la frase **exacta** (`bi` no casa con «bilingual»; `supply chain`, solo esa frase).

Las familias las genera la entrevista (`CONFIGURAR.md`) a partir de tus puestos y tu CV. Para adaptar el filtro basta con cambiar las familias: no hace falta escribir cada puesto. Las palabras de nivel o modalidad (intern, junior, senior, remote) no puntúan a propósito: que el detalle decida.

| familia | peso | raices | nota |
|---|---|---|---|
