# F6 · Reenviar un PDF

## Propósito
Volver a enviar a Telegram el PDF de un CV ya validado, sin cambiar su texto. La Action regenera el PDF desde el Markdown guardado y lo envía con su pie de siempre.

## Disparadores
- «Reenvíame el PDF de 4012345678»
- «No me llegó el CV de 4012345678 a Telegram»
- «Mándame otra vez el PDF de 4012345678»
- «Borré el mensaje de 4012345678, reenvíalo»
- «Regenera el PDF de 4012345678 sin cambiar el texto»
- «Vuelve a mandarme los PDF de 4012… y 4013…»

## Entradas
- Uno o varios `job_id`.

## Pasos

1. **Lee su situación:**
   ```sql
   SELECT e.job_id, e.estado, e.notificado_en, o.empresa, o.titulo
   FROM emparejamientos e JOIN ofertas o ON o.job_id = e.job_id WHERE e.job_id IN ('<ID1>', '<ID2>');
   ```
2. **Comprueba cada id:**
   - `validada`: se puede reenviar.
   - `validada` sin `notificado_en`: el envío ya está pendiente; basta con lanzar la Action.
   - `redactada`: aún no se validó; lanza la Action y llegará.
   - `rechazada`: no hay PDF; corrígelo con `F3`.
   - `sin_cv` o sin fila: no hay CV; genéralo con `F1`.
3. **Confirma** los ids que se reenviarán.
4. **Marca para reenvío** (una sentencia para todos):
   ```sql
   UPDATE emparejamientos SET notificado_en = NULL
   WHERE job_id IN ('<ID1>', '<ID2>') AND estado = 'validada';
   ```
5. **Comprueba:**
   ```sql
   SELECT job_id, estado, notificado_en FROM emparejamientos WHERE job_id IN ('<ID1>', '<ID2>');
   ```

## Respuesta
```
Listos para reenvío (2): 4012…, 4013…
```
Y el cierre con el enlace a la Action de las instrucciones del Project.

## Casos límite
- **Quiere cambios en el texto**, no solo el PDF: eso es un CV nuevo (`F1`), no un reenvío.
