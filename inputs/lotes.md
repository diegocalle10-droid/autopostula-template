# Lotes, pausas, cadencias y poda (parámetro de entrada)

Fuente única de los valores operativos. Los rangos se expresan como dos claves (`_min` y `_max`).
Los valores son conservadores a propósito: LinkedIn trata un ritmo alto como automatizado. Se ajustan con datos reales.
Regla de trabajo, fijada tras el primer 429 del proyecto (2026-10-31, con dos procesos de peticiones solapados): **entre 60 y 90 segundos por petición** (aleatorio dentro del rango, no una cadencia exacta) y **de 4 a 6 minutos entre lotes**. No hay tope diario: lo que cabe en las horas de `run-continuo --horas H` a este ritmo es el resultado.

## Búsqueda

| clave | valor | unidad | nota |
|---|---|---|---|
| consultas_por_lote | 5 | consultas | |
| pausa_entre_consultas_min | 60 | s | Dentro de un lote. Regla: entre 60 y 90 s por petición |
| pausa_entre_consultas_max | 90 | s | |
| pausa_entre_lotes_min | 4 | min | Entre lotes |
| pausa_entre_lotes_max | 6 | min | |
| jobage_dias_primer_barrido | 30 | días | Máximo de antigüedad de una oferta |
| max_paginas | 3 | páginas | Cada página es una petición más |
| umbral_pagina_nuevas | 0.5 | proporción | Se pide la página siguiente solo si la actual trajo al menos esta proporción de ofertas nuevas |
| umbral_pagina_perfil | 0.3 | proporción | Y solo si al menos esta proporción de los títulos de la actual pasa el filtro de `prefiltro.md`: en los mercados pequeños LinkedIn rellena las páginas siguientes con anuncios sin relación |
| margen_jobage_dias | 1 | días | Se suma al tiempo desde la última pasada |
| reintento_fallida_horas | 1 | h | Si una combinación falla (sin ser 429), se reintenta pasado este tiempo |

## Detalle

| clave | valor | unidad | nota |
|---|---|---|---|
| detail_por_lote | 10 | peticiones | |
| pausa_entre_detail_min | 60 | s | Regla: entre 60 y 90 s por petición |
| pausa_entre_detail_max | 90 | s | |
| pausa_entre_lotes_detail_min | 4 | min | Entre lotes |
| pausa_entre_lotes_detail_max | 6 | min | |
| detalles_pendientes_max | 0 | ofertas | Modo continuo (`run-continuo`): si hay más ofertas elegibles sin detalle que este valor, la siguiente petición es un detalle; si no, una búsqueda. 0 = el detalle va siempre antes de volver a buscar, y al parar no queda cola |

## Ejecución

No hay horario fijo: la captura corre cuando la lanzas y durante las horas que le digas. Lo normal es lanzarla al irte a dormir con `iniciar.bat`; al terminar avisa por Telegram y apaga el PC.

| clave | valor | unidad | nota |
|---|---|---|---|
| horas_por_defecto | 5 | h | Duración de la captura si al lanzarla no indicas otra. Tiene que terminar antes de la hora de la rutina de CV |
| bloqueo_caduca_horas | 12 | h | Un archivo de bloqueo más antiguo se considera abandonado y se ignora |
| apagar_tras_captura_min | 25 | min | Al terminar `run-continuo` (salvo con Ctrl+C) se avisa por Telegram y, pasado este tiempo, el PC se apaga (`shutdown /s`; `shutdown /a` lo cancela). 0 = no apagar. Solo Windows |

## Cadencia de mantenimiento

Cada cuántos días se repite una combinación, según la prioridad de su término.

| prioridad | cadencia_dias | nota |
|---|---|---|
| 1 | 10 | Se afina con datos reales |
| 2 | 20 | |

## Escalada del 429

Cada 429 o desafío anti-bot aplica **el primer escalón que se cumple**. `ocurrencias` cuenta el 429 actual más los anteriores dentro de `ventana_dias` (0 = hoy, desde la medianoche local).
Acciones: `pausa` (espera `horas`), `hasta_manana` y `parada_total` (espera `horas`; solo se levanta con `reanudar --forzar`). El CLI nunca reintenta un 429: la espera la fija esta tabla.

| ocurrencias | ventana_dias | accion | horas |
|---|---|---|---|
| 3 | 2 | parada_total | 8760 |
| 2 | 0 | hasta_manana | - |
| 1 | 0 | pausa | 3 |

## Disyuntor

| clave | valor | unidad | nota |
|---|---|---|---|
| vacios_seguidos_para_alerta | 3 | consultas | En combinaciones que antes devolvían datos |
| pausa_tras_vacios_horas | 3 | h | |
| fallos_seguidos_para_parada | 3 | peticiones | Búsquedas o detalles seguidos que fallan sin ser 429 |
| pausa_tras_fallos_horas | 3 | h | |
| fallos_por_oferta_para_descartar | 2 | intentos | Una oferta cuyo detalle llega sin contenido este número de veces se descarta con la regla `detalle_ilegible` de `decisiones.md` y se sigue con la siguiente |

## Poda

| clave | valor | unidad | nota |
|---|---|---|---|
| ubicacion_sin_resultados_terminos | 3 | términos | Una ubicación con 0 resultados en este número de términos pasa a cadencia máxima |
| ubicacion_sin_resultados_prioridad_max | 1 | prioridad | Solo cuentan los términos con esta prioridad o mejor |
| pasadas_sin_nuevas_para_duplicar | 3 | pasadas | Multiplica la cadencia de la combinación |
| factor_cadencia_poda | 2 | veces | Factor por el que se multiplica |
| cadencia_maxima_dias | 30 | días | Tope de la cadencia tras podar |

## Datos

| clave | valor | unidad | nota |
|---|---|---|---|
| huella_dias | 45 | días | Ventana para detectar republicaciones con la misma huella |
