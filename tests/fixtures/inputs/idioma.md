# Idioma: glosarios y reglas (parámetro de entrada)

Fuente única del filtro de idioma. Se comparan textos sin mayúsculas ni acentos.
Una expresión que empiece por `re:` es una expresión regular; el resto es texto literal.

Reglas generales:
- Un título en inglés **no descarta por sí solo**.
- Contenido mixto **no se descarta**: se aplica el glosario.
- Señales de ambos lados: gana la más exigente y la oferta pasa a `revisar`.
- Los niveles MCER (A2, B1…) solo cuentan a menos de `ventana_mcer_chars` de un alias del idioma vigilado.
- Una expresión de "Pasa" a menos de `ventana_negacion_chars` de una negación sigue siendo aceptable.

## Reglas

| clave | valor | nota |
|---|---|---|
| ventana_mcer_chars | 40 | Distancia máxima entre un alias del idioma vigilado y un nivel MCER |
| ventana_negacion_chars | 30 | Distancia máxima de una negación a una expresión del idioma vigilado |
| umbral_idioma_dominante | 0.65 | Proporción de palabras de un idioma para declararlo dominante; por debajo es "mixto" |
| minimo_palabras_detectadas | 6 | Con menos palabras reconocidas, el idioma se da por indeterminado |
| idioma_propio | es | Idioma en el que quieres trabajar. Debe tener fila en «Palabras de idioma» y «Palabras de título» |
| idioma_vigilado | en | Idioma cuyo nivel exigido se vigila. Debe tener fila en esas mismas tablas |

## Alias del idioma vigilado

Cómo se nombra el idioma vigilado en un anuncio; los niveles MCER solo cuentan junto a uno de estos nombres.

| alias |
|---|
| inglés |
| english |

## Pasa

Nivel aceptable del idioma vigilado.

| categoria | expresion |
|---|---|
| tecnico | inglés técnico |
| tecnico | technical english |
| tecnico | inglés técnico escrito |
| tecnico | inglés para lectura técnica |
| lectura | lectura de documentación en inglés |
| lectura | documentación en inglés |
| lectura | leer documentación técnica |
| lectura | reading proficiency |
| lectura | manuales en inglés |
| lectura | capacidad de leer en inglés |
| lectura | comprensión lectora en inglés |
| lectura | inglés escrito básico |
| lectura | inglés a nivel de lectura |
| intermedio | inglés intermedio |
| intermedio | intermediate english |
| intermedio | nivel intermedio de inglés |
| intermedio | inglés medio |
| intermedio | conversational english |
| intermedio | intermediate-high |
| deseable | inglés deseable |
| deseable | inglés valorable |
| deseable | se valora inglés |
| deseable | se valorará inglés |
| deseable | english is a plus |
| deseable | nice to have |
| deseable | no excluyente |
| deseable | no indispensable |
| basico | nivel básico de inglés |
| basico | inglés básico |
| basico | algún conocimiento de inglés |
| basico | conocimientos de inglés |
| basico | manejo de inglés a nivel técnico |

## Rechaza

Inglés fluido o exigente.

| categoria | expresion |
|---|---|
| fluido | inglés avanzado |
| fluido | inglés fluido |
| fluido | fluent english |
| fluido | advanced english |
| fluido | excellent command of english |
| fluido | full professional proficiency |
| fluido | business fluent |
| nativo | bilingüe |
| nativo | bilingual |
| nativo | native english |
| nativo | inglés nativo |
| nativo | native speaker |
| excluyente | inglés excluyente |
| excluyente | inglés indispensable |
| excluyente | inglés obligatorio |
| excluyente | english required |
| excluyente | must speak english |
| excluyente | imprescindible inglés |
| entrevista | entrevista en inglés |
| entrevista | interview in english |
| entrevista | reuniones en inglés con clientes |
| entrevista | trato con clientes en inglés |
| entrevista | daily communication in english |
| alto | excelente nivel de inglés |
| alto | alto nivel de inglés |
| alto | nivel alto de inglés |
| alto | dominio del inglés |
| alto | strong english skills |

## Niveles MCER

| nivel | clase |
|---|---|
| a1 | pasa |
| a2 | pasa |
| b1 | pasa |
| b2 | pasa |
| c1 | rechaza |
| c2 | rechaza |

## Negaciones

| expresion |
|---|
| sin |
| no requiere |
| no se requiere |
| no es necesario |
| no necesita |
| not required |
| no need |
| without |

## Palabras de idioma

Para detectar el idioma de una descripción por recuento de palabras funcionales.

| idioma | palabras |
|---|---|
| es | de, la, el, en, y, que, los, las, del, para, con, por, un, una, se, su, al, como, más, o, sus, este, entre, sobre, también, nuestro, nuestra, tu, te, experiencia, equipo, trabajo |
| en | the, and, of, to, in, for, with, you, our, will, is, are, on, as, be, an, or, your, we, this, that, from, by, at, experience, team, work, skills |

## Palabras de título

Para detectar el idioma de un título (suele ser corto y sin palabras funcionales).

| idioma | palabras |
|---|---|
| es | analista, ingeniero, ingeniera, coordinador, coordinadora, especialista, gestor, gestora, responsable, consultor, consultora, administrador, administradora, técnico, técnica, desarrollador, desarrolladora, jefe, director, directora, asistente, auxiliar, de, en, y, con, para, remoto, datos, procesos, operaciones, calidad, logístico, logística, negocio, soporte, automatización |
| en | analyst, engineer, manager, specialist, developer, consultant, administrator, architect, lead, head, director, associate, senior, junior, officer, coordinator, of, for, and, with, remote, data, process, operations, quality, support, business, automation |
