<!--
Plantilla del CV a medida. La Action la rellena para cada oferta (collector/cv/componer.py):
- {{fijo:...}}: lo copia el código del CV base elegido, tal cual. La rutina no lo escribe.
- {{rutina:...}}: lo redacta la rutina en `emparejamientos.contenido`.
- El bloque {{#puesto}}...{{/puesto}} se repite por cada puesto del CV base, en su orden.
Los títulos de sección y su orden son estos; cambiarlos es editar este archivo. Este comentario no sale en el CV.
-->
# {{fijo:nombre}}

{{rutina:titular}}

{{fijo:contacto}}

## PERFIL PROFESIONAL

{{rutina:perfil}}

## EXPERIENCIA PROFESIONAL

{{#puesto}}
### {{rutina:cargo}}

{{fijo:empresa_fechas}}

{{rutina:vinetas}}
{{/puesto}}

## FORMACIÓN PROFESIONAL

{{fijo:formacion}}

## CERTIFICACIONES

{{fijo:certificaciones}}

## STACK TÉCNICO

{{rutina:stack}}

{{fijo:idiomas}}
