-- Mensajes para Telegram que deja la rutina de la nube (resumen, "nada por redactar", ids que no pudo registrar).
-- GitHub Actions los envía y marca `enviado_en`. Va aparte de 001 porque usa sintaxis que solo entiende PostgreSQL.
CREATE TABLE avisos (
  aviso_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  creado_en  TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
  texto      TEXT NOT NULL,
  enviado_en TEXT,
  tipo       TEXT NOT NULL DEFAULT 'texto'   -- el último `resumen` marca desde cuándo cuenta el siguiente resumen de la rutina
);
CREATE INDEX ix_avisos_pendientes ON avisos (aviso_id) WHERE enviado_en IS NULL;
