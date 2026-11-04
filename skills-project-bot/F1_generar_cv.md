# F1 · Generar CV para una oferta concreta

## Propósito
Redactar el CV a medida de una oferta que el usuario elige, **sin umbral de afinidad**: normalmente una que quedó `sin_cv`, una oferta que acaba de marcar como apta o una que quiere rehacer desde cero. El CV queda en `redactada` y la Action lo valida, genera el PDF y lo envía.

## Entradas
- `job_id` (obligatorio).
- CV base preferido (opcional): si el usuario lo nombra, úsalo; si no, elige por afinidad.

## Pasos

1. **Lee la oferta y su situación:**
   ```sql
   SELECT o.job_id, o.titulo, o.empresa, o.ubicacion, o.modalidad, o.url, o.estado, o.descripcion,
          e.estado AS emparejamiento, e.cv_id, e.afinidad, e.intentos
   FROM ofertas o LEFT JOIN emparejamientos e ON e.job_id = o.job_id
   WHERE o.job_id = '<JOB_ID>';
   ```
2. **Comprueba antes de redactar:**
   - Sin filas: el id no existe. Díselo y para.
   - `descripcion` vacía: la captura aún no pidió el detalle de esta oferta. No se puede redactar; díselo y para.
   - `emparejamiento = 'rechazada'`: no es F1, es `F3_corregir_rechazo.md`.
   - `emparejamiento` en `redactada`: ya hay un CV esperando validación. Pregunta si quiere sustituirlo.
   - `emparejamiento` en `validada`: ya tiene CV y PDF. Pregunta si quiere uno nuevo o solo el PDF otra vez (`F6`).
3. **Lee las fuentes del repositorio** del usuario (rama `main`):
   - `inputs/cv.md`: la tabla de CV base (id y archivo).
   - Los CV base de `CV/base/` que vayas a comparar.
   - `CV/PROMPT_RUTINA.md`, secciones **3.1** (afinidad y elección), **3.2** (reescritura) y **3.3** (estilo). Aplícalas tal cual, con una única excepción: **aquí no hay umbral**; redacta aunque la afinidad quede por debajo.
4. **Elige el CV base** con el método de 3.1 (o el que pidió el usuario) y calcula la afinidad igualmente: se guarda como dato.
5. **Redacta el CV** siguiendo 3.2 y 3.3, incluido el proceso borrador, auditoría y final.
6. **Confirma con el usuario:** empresa, título, CV base elegido, afinidad y que vas a registrar el CV. Si pidió ver el texto, enséñaselo antes.
7. **Registra** (sirve tanto si no había emparejamiento como si había uno en `sin_cv`, `redactada` o `validada`):
   ```sql
   INSERT INTO emparejamientos (job_id, estado, cv_id, afinidad, requisitos_cubiertos, requisitos_faltantes, cv_md, emparejado_en)
   VALUES ('<JOB_ID>', 'redactada', '<CV_ID>', <AFINIDAD>, $t$<req1, req2>$t$, $t$<req3, req4>$t$,
           $cv$<MARKDOWN COMPLETO>$cv$, to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
   ON CONFLICT (job_id) DO UPDATE SET estado = 'redactada', cv_id = EXCLUDED.cv_id, afinidad = EXCLUDED.afinidad,
     requisitos_cubiertos = EXCLUDED.requisitos_cubiertos, requisitos_faltantes = EXCLUDED.requisitos_faltantes,
     cv_md = EXCLUDED.cv_md, motivo = NULL, rechazo = NULL, intentos = 0, validado_en = NULL, notificado_en = NULL,
     emparejado_en = EXCLUDED.emparejado_en;
   ```
   El texto libre va entre dólares (`$t$…$t$`, y `$cv$…$cv$` para el CV) para no escapar comillas.
8. **Comprueba:**
   ```sql
   SELECT job_id, estado, cv_id, afinidad, length(cv_md) AS caracteres FROM emparejamientos WHERE job_id = '<JOB_ID>';
   ```

## Respuesta
```
CV registrado · <empresa> · <título>
ID: <job_id>
CV base <cv_id> · afinidad <N> %
```
Y el cierre con el enlace a la Action de las instrucciones del Project.

## Casos límite
- **Varios ids**: procesa uno a uno; confirma la lista entera al principio y registra cada uno con su sentencia. Al final, un solo enlace a la Action.
- **Oferta `descartada` o `revisar`**: se puede generar igualmente si el usuario lo pide; su estado en `ofertas` no cambia. Si además quiere marcarla apta, eso es `F2`.
- **Antes de registrar**, repasa el CV contra la tabla de motivos de rechazo de `F3_corregir_rechazo.md`: es lo que comprueba la validación.
