-- CV gobernado por keywords (runbook v7). La rutina guarda, por oferta, sus keywords con el respaldo del CV base
-- (`keywords`), lo que redacta (`contenido`).
-- La Action compone `cv_md` con CV/plantilla.md + datos fijos del CV base + `contenido`, comprueba la cobertura y
-- recalcula la afinidad. Una fila redactada trae `cv_md` (flujo anterior) o `contenido` (flujo v7).
ALTER TABLE emparejamientos ADD COLUMN keywords JSONB, ADD COLUMN contenido JSONB;
ALTER TABLE emparejamientos DROP CONSTRAINT IF EXISTS emparejamientos_check1;
ALTER TABLE emparejamientos ADD CONSTRAINT emparejamientos_redactada_check
  CHECK (estado = 'sin_cv' OR (cv_id IS NOT NULL AND afinidad IS NOT NULL AND (cv_md IS NOT NULL OR contenido IS NOT NULL)));

-- Al corregir un rechazo, la rutina reutiliza las keywords que ya guardó.
CREATE OR REPLACE VIEW ofertas_por_redactar AS
SELECT o.job_id, o.titulo, o.empresa, o.ubicacion, o.pais, o.modalidad, o.url, o.descripcion,
       e.rechazo, COALESCE(e.intentos, 0) AS intentos, e.keywords
FROM ofertas o LEFT JOIN emparejamientos e ON e.job_id = o.job_id
WHERE (o.estado = 'apta' AND e.job_id IS NULL) OR (e.estado = 'rechazada' AND e.intentos < 3);
