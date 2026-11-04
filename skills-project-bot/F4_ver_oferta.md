# F4 · Ver una oferta

## Propósito
Contar al usuario todo lo que el sistema sabe de una oferta: datos, estado, por qué está así, su CV y si ya se envió. Solo lectura.

## Entradas
- `job_id`. Si el usuario da la empresa o el título en vez del id, búscalo:
  ```sql
  SELECT job_id, empresa, titulo, estado FROM ofertas
  WHERE empresa ILIKE '%<texto>%' OR titulo ILIKE '%<texto>%' ORDER BY fecha_hallazgo DESC LIMIT 10;
  ```

## Pasos

1. **Una sola consulta con todo:**
   ```sql
   SELECT o.job_id, o.titulo, o.empresa, o.ubicacion, o.pais, o.modalidad, o.modalidad_detectada, o.url,
          o.fecha_publicacion, o.fecha_hallazgo, o.estado, o.motivo_descarte, o.revisada_en, o.nivel_idioma,
          o.descripcion IS NOT NULL AS con_detalle,
          e.estado AS emparejamiento, e.cv_id, e.afinidad, e.requisitos_cubiertos, e.requisitos_faltantes,
          e.motivo, e.rechazo, e.intentos, e.emparejado_en, e.validado_en, e.notificado_en
   FROM ofertas o LEFT JOIN emparejamientos e ON e.job_id = o.job_id WHERE o.job_id = '<JOB_ID>';
   ```
   Si pide la descripción o el CV, añade `o.descripcion` o `e.cv_md` a la consulta y muéstralos.
2. **Interpreta el estado** con la tabla de abajo.

## Respuesta
```
<empresa> · <título>
ID: <job_id>
<ubicación> · <modalidad> · publicada <fecha>
Estado: <estado de la oferta> (<motivo si lo hay>)
CV: <estado del emparejamiento> · <cv_id> · afinidad <N> %
<una línea con lo que significa y el siguiente paso>
<url>
```

## Cómo leer la situación

| Oferta / emparejamiento | Significa | Siguiente paso posible |
|---|---|---|
| `pendiente`, sin detalle | La captura aún no pidió su descripción | Esperar a la próxima captura |
| `revisar` | El capturador dudó; el porqué está en `motivo_descarte`. | Decidir con `F2` |
| `descartada` | Descartada por una regla (o por el usuario si hay `revisada_en`) | Recuperarla con `F2` si interesa |
| `apta`, sin emparejamiento | La rutina la redactará en su próxima ejecución | Generarla ya con `F1` |
| `sin_cv` | Ningún CV llegaba al umbral de `inputs/cv.md`; `motivo` dice qué faltaba | Generarla igualmente con `F1` |
| `redactada` | CV escrito, esperando la Action | Lanzar la Action |
| `rechazada` | La validación lo rechazó (`rechazo`); si ya no está en `ofertas_por_redactar`, agotó los intentos y la rutina no lo reintenta | Corregir con `F3` |
| `validada` con `notificado_en` | PDF generado y enviado | Reenviar con `F6` si hace falta |
| `validada` sin `notificado_en` | PDF generado, envío pendiente | Lanzar la Action |

Motivos de `revisar` y de descarte: `inputs/decisiones.md` del repositorio.
