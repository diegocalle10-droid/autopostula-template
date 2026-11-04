# F5 · Ver lo pendiente

## Propósito
Dar al usuario una foto de lo que requiere su atención y de lo que está en marcha. Solo lectura, **en una sola consulta**.

## Disparadores
- «¿Qué tengo pendiente?»
- «¿Qué hay por revisar?»
- «Lista las ofertas sin CV»
- «¿Cuántos CV se enviaron hoy?»
- «¿Hay rechazos agotados?»
- «¿Qué falta por hacer?» / «¿cómo va todo?»
- «Resumen del estado del sistema»
- «¿Qué va a redactar la rutina la próxima vez?»
- «¿Cuántas aptas hay sin CV?»

## Pasos

1. **Una consulta para todo** (si el usuario pregunta por un solo grupo, ejecútala igual y muestra solo ese grupo):
   ```sql
   SELECT 'por_revisar' AS grupo, o.job_id, o.empresa, o.titulo, o.motivo_descarte AS detalle
     FROM ofertas o WHERE o.estado = 'revisar'
   UNION ALL
   SELECT 'sin_cv', e.job_id, o.empresa, o.titulo, concat(e.afinidad, ' % · ', e.motivo)
     FROM emparejamientos e JOIN ofertas o ON o.job_id = e.job_id WHERE e.estado = 'sin_cv'
   UNION ALL
   SELECT 'rechazo_agotado', e.job_id, o.empresa, o.titulo, e.rechazo
     FROM emparejamientos e JOIN ofertas o ON o.job_id = e.job_id WHERE e.estado = 'rechazada' AND e.intentos >= 3
   UNION ALL
   SELECT 'rechazo_en_curso', e.job_id, o.empresa, o.titulo, concat('intento ', e.intentos, ' · ', e.rechazo)
     FROM emparejamientos e JOIN ofertas o ON o.job_id = e.job_id WHERE e.estado = 'rechazada' AND e.intentos < 3
   UNION ALL
   SELECT 'esperando_action', e.job_id, o.empresa, o.titulo,
          CASE WHEN e.estado = 'redactada' THEN 'por validar' ELSE 'PDF sin enviar' END
     FROM emparejamientos e JOIN ofertas o ON o.job_id = e.job_id
     WHERE e.estado = 'redactada' OR (e.estado = 'validada' AND e.notificado_en IS NULL)
   UNION ALL
   SELECT 'por_redactar', v.job_id, v.empresa, v.titulo, CASE WHEN v.intentos > 0 THEN 'reescritura' ELSE 'nueva' END
     FROM ofertas_por_redactar v
   UNION ALL
   SELECT 'pendiente_detalle', o.job_id, o.empresa, o.titulo, o.pais
     FROM ofertas o WHERE o.estado = 'pendiente'
   UNION ALL
   SELECT 'enviado_24h', e.job_id, o.empresa, o.titulo, concat(e.cv_id, ' · ', e.afinidad, ' %')
     FROM emparejamientos e JOIN ofertas o ON o.job_id = e.job_id
     WHERE e.notificado_en >= to_char(now() AT TIME ZONE 'utc' - interval '24 hours', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
       AND e.estado = 'validada'
   ORDER BY 1, 2;
   ```

## Respuesta
Primero los recuentos en una línea; después, solo los grupos con filas, en este orden y con su siguiente paso:

```
Por revisar 12 · Sin CV 3 · Rechazos agotados 1 · Esperando Action 2 · Por redactar 5 · Pendientes de detalle 53 · Enviados (24 h) 18

Requieren tu decisión
• Por revisar (12) → decide con «marca … apta / descartada»
  | ID | Empresa | Título | Motivo |
• Sin CV (3) → si alguna te interesa, «genera el CV para …»
• Rechazos agotados (1) → «corrige el rechazo de …»

En marcha
• Esperando Action (2) → lanza la Action: <enlace>
• Por redactar (5) → la rutina las hará en su próxima ejecución
• Pendientes de detalle (53) → la próxima captura pedirá su detalle a LinkedIn; después las reglas decidirán (apta, revisar o descartada)
• Enviados en las últimas 24 h (18)
```

Tabla con `ID | Empresa | Título | Detalle` para cada grupo de hasta 15 filas; si hay más, las 15 primeras y «… y N más». Si todo está vacío: «No hay nada pendiente».
