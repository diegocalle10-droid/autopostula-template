-- Revisión manual en Neon: con fecha, la subida desde el capturador ya no toca la fila.
ALTER TABLE ofertas ADD COLUMN revisada_en TEXT;
-- Tipo de aviso: el último `resumen` marca desde cuándo cuenta el siguiente resumen de la rutina.
ALTER TABLE avisos ADD COLUMN tipo TEXT NOT NULL DEFAULT 'texto';
