-- Mensajes para Telegram que deja la rutina de la nube (resumen, "nada por redactar", ids que no pudo registrar).
-- GitHub Actions los envía y marca `enviado_en`.
CREATE TABLE avisos (
  aviso_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  creado_en  TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
  texto      TEXT NOT NULL,
  enviado_en TEXT
);
CREATE INDEX ix_avisos_pendientes ON avisos (aviso_id) WHERE enviado_en IS NULL;
