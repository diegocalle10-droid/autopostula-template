# F2 · Marcar ofertas como aptas o descartadas

## Propósito
Aplicar la decisión del usuario sobre una o varias ofertas, sobre todo las que el capturador dejó en `revisar`. Una oferta marcada `apta` entra sola en la próxima ejecución de la rutina; una `descartada` deja de aparecer. La fecha en `revisada_en` protege la decisión: el capturador ya no puede cambiar esa fila.

## Disparadores
- «Marca 4012345678 como apta»
- «Descarta la 4012345678, no me interesa»
- «4012… apta, 4013… descartada, 4014… apta»
- «Esta que estaba a revisar sí me vale: 4012345678»
- «La de modalidad híbrida, 4012345678, descártala»
- «Pasa a apta todas las de idioma aceptable»
- «Recupera la 4012345678, la descartaste pero sí me interesa»
- «Ya revisé las 12: aptas 4012… y 4013…, el resto descartadas»

## Entradas
- Para cada oferta: `job_id` y la decisión (`apta` o `descartada`).
- Si el usuario describe un grupo en vez de ids («todas las de idioma aceptable», «el resto»), resuélvelo con la consulta del paso 1 y enséñale la lista de ids antes de escribir.

## Pasos

1. **Lee las ofertas afectadas:**
   ```sql
   SELECT job_id, empresa, titulo, estado, motivo_descarte, revisada_en, descripcion IS NOT NULL AS con_detalle
   FROM ofertas WHERE job_id IN ('<ID1>', '<ID2>');
   ```
   Para grupos («todas las que están a revisar»):
   ```sql
   SELECT job_id, empresa, titulo, motivo_descarte FROM ofertas WHERE estado = 'revisar' ORDER BY fecha_hallazgo DESC;
   ```
2. **Comprueba:**
   - Id que no aparece: díselo y sigue con el resto.
   - **No marques `apta` una oferta con `con_detalle = false`**: aún no tiene descripción y la rutina no podría redactar su CV. Además, al quedar revisada, la captura ya no podría completarla. Explícaselo y déjala como está.
   - Oferta que ya está en el estado pedido: no hace falta escribir; díselo.
3. **Confirma** con una tabla: `job_id`, empresa, título, estado actual → estado nuevo.
4. **Marca las aptas** (una sentencia para todas):
   ```sql
   UPDATE ofertas SET estado = 'apta', revisada_en = to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
   WHERE job_id IN ('<ID1>', '<ID2>');
   ```
5. **Marca las descartadas** (una sentencia para todas). El motivo original se conserva; si no había, queda `descarte_manual`:
   ```sql
   UPDATE ofertas SET estado = 'descartada', motivo_descarte = COALESCE(motivo_descarte, 'descarte_manual'),
          revisada_en = to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
   WHERE job_id IN ('<ID3>', '<ID4>');
   ```
6. **Comprueba:**
   ```sql
   SELECT job_id, estado, revisada_en FROM ofertas WHERE job_id IN ('<ID1>', '<ID2>', '<ID3>', '<ID4>');
   ```

## Respuesta
```
Marcadas como aptas (2): 4012…, 4013…
Marcadas como descartadas (1): 4014…
Las aptas se redactarán en la próxima ejecución de la rutina.
```
Si el usuario quiere el CV ya, ofrécele `F1` para esas ids.

## Casos límite
- **Oferta apta que ya tiene emparejamiento** (`sin_cv`, por ejemplo): marcarla apta no hace que la rutina la redacte, porque ya pasó por ella. Para tener CV, usa `F1`.
- **Recuperar una descartada**: es el mismo paso 4. Si su motivo era automático, se conserva como historial.
- **Qué significa cada motivo de `revisar`**: los motivos y la condición que los produce están en `inputs/decisiones.md` del repositorio (tablas «Reglas de decisión» y «Condiciones»). Léelo de ahí si el usuario pregunta.
