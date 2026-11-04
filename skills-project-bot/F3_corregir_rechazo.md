# F3 · Corregir un CV rechazado

## Propósito
Arreglar un CV que la validación automática rechazó, sobre todo cuando ya agotó los intentos de la rutina (`intentos_maximos` de `inputs/mensajes/parametros.md`). Corriges exactamente lo que dice el motivo, revisas el resto de reglas y lo devuelves a `redactada` para que la Action lo valide otra vez.

## Disparadores
- «Corrige el rechazo de 4012345678»
- «Arregla el CV de 4012345678, lo rechazaron por la raya larga»
- «El CV de 4012345678 se pasa de páginas, recórtalo»
- «¿Por qué rechazaron 4012345678? Arréglalo»
- «Se agotaron los intentos de 4012345678, corrígelo tú»
- «Repara los CV rechazados» (lista y corrige uno a uno)
- «4012345678 tiene un fallo en las fechas, corrígelo»

## Entradas
- `job_id`. Para «todos los rechazados», obtén la lista con:
  ```sql
  SELECT e.job_id, o.empresa, o.titulo, e.intentos, e.rechazo FROM emparejamientos e
  JOIN ofertas o ON o.job_id = e.job_id WHERE e.estado = 'rechazada' ORDER BY e.intentos DESC, e.job_id;
  ```

## Pasos

1. **Lee el CV rechazado y su oferta:**
   ```sql
   SELECT e.job_id, e.estado, e.cv_id, e.afinidad, e.intentos, e.rechazo, e.cv_md, o.empresa, o.titulo, o.descripcion
   FROM emparejamientos e JOIN ofertas o ON o.job_id = e.job_id WHERE e.job_id = '<JOB_ID>';
   ```
   Si `estado` no es `rechazada`, no es esta skill: díselo (si no tiene CV, `F1`; si está `validada`, no hay nada que corregir).
2. **Lee las fuentes del repositorio** del usuario: el CV base `cv_id` (archivo en `inputs/cv.md`) y las reglas de `CV/PROMPT_RUTINA.md`, secciones 3.2 y 3.3.
3. **Corrige el motivo** con la tabla de abajo y repasa el CV entero contra las demás reglas: un arreglo no debe introducir otro fallo.
4. **Confirma con el usuario:** el motivo, qué cambiaste en una o dos líneas, y que vas a registrarlo.
5. **Registra:**
   ```sql
   UPDATE emparejamientos SET estado = 'redactada', cv_md = $cv$<MARKDOWN CORREGIDO>$cv$,
          intentos = LEAST(intentos, 2), emparejado_en = to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
   WHERE job_id = '<JOB_ID>' AND estado = 'rechazada';
   ```
   `LEAST(intentos, 2)`: si la validación lo vuelve a rechazar, contará como intento 3 y el usuario recibirá el aviso. `rechazo` se queda como está; la Action lo borra al aceptar el CV.
6. **Comprueba:**
   ```sql
   SELECT job_id, estado, intentos, length(cv_md) AS caracteres FROM emparejamientos WHERE job_id = '<JOB_ID>';
   ```

## Motivos de rechazo y cómo se corrigen

| El motivo dice… | Corrección |
|---|---|
| `ocupa N páginas (máximo 2)` | Recorta lo menos relevante para la oferta hasta quedar claramente por debajo de 1.400 palabras (apunta a unas 1.250). |
| `el texto contiene la raya larga «—»` | Cámbiala por coma, punto, dos puntos o paréntesis en perfil y logros. En cargos, líneas de empresa y fechas, certificaciones y contacto se deja como en el CV base. |
| `contiene un marcador o texto de plantilla sin resolver: «…»` | Quita lo citado: corchetes `[…]`, llaves `{…}`, cualquier `<…>`, `TODO`, `XXX` o «lorem ipsum». No uses `<` ni `>` en el texto. |
| `el nombre «…» no coincide` | Copia el nombre (`#`) literal del CV base. |
| `correo / enlace / teléfono del contacto ausente o añadido` | Copia la línea de contacto literal del CV base. |
| `la empresa o las fechas del puesto «…» no coinciden` | La línea bajo el título del cargo (empresa y fechas) debe ser idéntica a una del CV base. El título del cargo sí puede cambiar. |
| `estudios: «…» no está en el CV base` / `certificaciones: «…»` | Copia esas líneas literales del CV base; solo se pueden omitir, nunca cambiar. |
| `idioma «…» no está en el CV base` | Deja el idioma y su nivel exactamente como en el CV base. |
| `CV base desconocido «…»` | `cv_id` debe ser uno de los ids de `inputs/cv.md`. Corrige el CV base elegido (con `F1` si hay que rehacerlo). |
| `el archivo está vacío` | El CV se perdió: rehazlo con `F1`. |

## Respuesta
```
Corregido · <empresa> · <título>
ID: <job_id>
Motivo: <motivo>. Cambio: <qué hiciste>.
```
Y el cierre con el enlace a la Action de las instrucciones del Project.

## Casos límite
- **Varios rechazados**: corrige y registra uno a uno; un solo enlace a la Action al final.
- **El motivo pide algo imposible sin cambiar datos fijos**: no lo fuerces. Explícaselo al usuario y propón rehacer con otro CV base (`F1`).
