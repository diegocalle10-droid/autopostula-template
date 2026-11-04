-- Fuera el estado con_pdf y sus columnas (ruta_pdf, pdf_en): eran de un flujo que no se usa. El PDF lo genera la Action
-- y lo envía por Telegram; el último estado es validada. Idempotente: sirve también sobre un 001 ya sin esas columnas.
ALTER TABLE emparejamientos DROP COLUMN IF EXISTS ruta_pdf, DROP COLUMN IF EXISTS pdf_en;
ALTER TABLE emparejamientos DROP CONSTRAINT IF EXISTS emparejamientos_estado_check;
ALTER TABLE emparejamientos ADD CONSTRAINT emparejamientos_estado_check CHECK (estado IN ('sin_cv','redactada','rechazada','validada'));
