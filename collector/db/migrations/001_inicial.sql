-- Base local (SQLite): búfer de la captura antes de subir a Neon. Las tablas de la captura llevan los mismos campos
-- y CHECK que en collector/online/migrations/001_neon.sql; aquí se añade la cola de subida (sección 7).
-- 1. OFERTAS ---------------------------------------------------------------
CREATE TABLE ofertas (
  job_id               TEXT    PRIMARY KEY,         -- id numérico de LinkedIn; NO se genera en local
  url                  TEXT    NOT NULL,
  titulo               TEXT    NOT NULL,
  empresa              TEXT,
  ubicacion            TEXT,                        -- tal cual la devuelve LinkedIn
  pais                 TEXT,                        -- normalizado con la tabla de países aceptados; NULL si no mapea
  fecha_publicacion    TEXT,
  fecha_hallazgo       TEXT    NOT NULL,            -- primera vez que se vio
  ultima_vista         TEXT    NOT NULL,            -- última vez que apareció en una búsqueda

  descripcion          TEXT,                        -- NULL = detalle aún no pedido
  detalle_obtenido_en  TEXT,                        -- NULL = pendiente de `detail`
  tipo_empleo          TEXT,
  activa               INTEGER,                     -- 1 = sin banner de cerrada; NULL = sin detalle
  modalidad            TEXT    NOT NULL,            -- la pedida en la búsqueda (valor de inputs/)
  modalidad_detectada  TEXT,                        -- la hallada en la descripción; NULL = sin indicio

  idioma_titulo        TEXT,                        -- código del idioma (inputs/idioma.md) o 'mixto'
  idioma_contenido     TEXT,
  nivel_idioma         TEXT,                        -- nivel exigido del idioma vigilado

  estado               TEXT    NOT NULL DEFAULT 'pendiente',
  motivo_descarte      TEXT,                        -- motivo de la regla que decidió (inputs/decisiones.md)
  huella               TEXT,                        -- hash(empresa|titulo|ubicacion) normalizado
  duplicada_de         TEXT    REFERENCES ofertas(job_id),

  CHECK (estado IN ('pendiente','apta','revisar','descartada')),
  CHECK (activa IS NULL OR activa IN (0,1)),
  CHECK (nivel_idioma IS NULL OR nivel_idioma IN ('ninguno','aceptable','exigente','dudoso')),
  CHECK (estado <> 'descartada' OR motivo_descarte IS NOT NULL)
);
CREATE INDEX ix_ofertas_huella      ON ofertas (huella);
CREATE INDEX ix_ofertas_estado      ON ofertas (estado);
CREATE INDEX ix_ofertas_hallazgo    ON ofertas (fecha_hallazgo);
CREATE INDEX ix_ofertas_sin_detalle ON ofertas (job_id) WHERE detalle_obtenido_en IS NULL;

-- 2. KEYWORDS --------------------------------------------------------------
CREATE TABLE oferta_keywords (
  job_id   TEXT NOT NULL REFERENCES ofertas(job_id) ON DELETE CASCADE,
  keyword  TEXT NOT NULL,                           -- término de inputs/puestos.md hallado en la descripción
  PRIMARY KEY (job_id, keyword)
);
CREATE INDEX ix_keywords_keyword ON oferta_keywords (keyword);

-- 3. COMBINACIONES (calendario y poda) ------------------------------------
CREATE TABLE combinaciones (
  combinacion_id      INTEGER PRIMARY KEY,
  termino             TEXT    NOT NULL,
  ubicacion_frase     TEXT    NOT NULL,
  prioridad           INTEGER NOT NULL,             -- 1 = más alta
  cadencia_dias       INTEGER NOT NULL,             -- vigente; puede crecer por poda
  ultima_ejecucion    TEXT,
  proxima_ejecucion   TEXT,
  pasadas_sin_nuevas  INTEGER NOT NULL DEFAULT 0,
  activa              INTEGER NOT NULL DEFAULT 1,
  UNIQUE (termino, ubicacion_frase),
  CHECK (prioridad >= 1),
  CHECK (cadencia_dias >= 1),
  CHECK (activa IN (0,1))
);
CREATE INDEX ix_comb_proxima ON combinaciones (activa, proxima_ejecucion, prioridad);

-- 4. CONSULTAS (cada petición de búsqueda) ---------------------------------
CREATE TABLE consultas (
  consulta_id     INTEGER PRIMARY KEY,
  combinacion_id  INTEGER NOT NULL REFERENCES combinaciones(combinacion_id),
  pagina          INTEGER NOT NULL DEFAULT 1,
  jobage_dias     INTEGER NOT NULL,
  ejecutada_en    TEXT    NOT NULL,
  resultado       TEXT    NOT NULL,
  n_resultados    INTEGER,
  n_nuevos        INTEGER,                          -- ofertas que no existían en `ofertas`
  codigo_error    TEXT,
  CHECK (resultado IN ('ok','vacia','fallida','desafio')),
  CHECK (pagina >= 1)
);
CREATE INDEX ix_consultas_dia  ON consultas (ejecutada_en);
CREATE INDEX ix_consultas_comb ON consultas (combinacion_id, ejecutada_en);

-- 5. HALLAZGOS (varias consultas pueden encontrar la misma oferta) ---------
CREATE TABLE hallazgos (
  job_id       TEXT    NOT NULL REFERENCES ofertas(job_id)     ON DELETE CASCADE,
  consulta_id  INTEGER NOT NULL REFERENCES consultas(consulta_id),
  PRIMARY KEY (job_id, consulta_id)
);

-- 6. EVENTOS (disyuntor y salud) -------------------------------------------
CREATE TABLE eventos (
  evento_id     INTEGER PRIMARY KEY,
  ocurrido_en   TEXT NOT NULL,
  tipo          TEXT NOT NULL,
  contexto      TEXT,
  pausa_hasta   TEXT,
  CHECK (tipo IN ('429','vacios_repetidos','fallo'))
);
CREATE INDEX ix_eventos_pausa ON eventos (pausa_hasta);

-- 7. COLA DE SINCRONIZACIÓN CON NEON ------------------------------------------
-- Los disparadores anotan cada fila insertada, cambiada o borrada; `online-subir` la vacía al terminar la ejecución.
-- (Los disparadores usan ON CONFLICT DO NOTHING: un INSERT OR IGNORE interno lo anula el upsert de la sentencia que lo dispara.)
-- Una fila de la cola se borra solo después de que Neon confirme el cambio, así que un corte se retoma donde quedó.
CREATE TABLE sync_pendientes (
  tabla  TEXT NOT NULL,
  k1     TEXT NOT NULL,
  k2     TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (tabla, k1, k2)
);

CREATE TRIGGER sync_ofertas_i AFTER INSERT ON ofertas BEGIN
  INSERT INTO sync_pendientes (tabla, k1) VALUES ('ofertas', NEW.job_id) ON CONFLICT DO NOTHING; END;
CREATE TRIGGER sync_ofertas_u AFTER UPDATE ON ofertas BEGIN
  INSERT INTO sync_pendientes (tabla, k1) VALUES ('ofertas', NEW.job_id) ON CONFLICT DO NOTHING; END;
CREATE TRIGGER sync_ofertas_d AFTER DELETE ON ofertas BEGIN
  INSERT INTO sync_pendientes (tabla, k1) VALUES ('ofertas', OLD.job_id) ON CONFLICT DO NOTHING; END;

CREATE TRIGGER sync_keywords_i AFTER INSERT ON oferta_keywords BEGIN
  INSERT INTO sync_pendientes VALUES ('oferta_keywords', NEW.job_id, NEW.keyword) ON CONFLICT DO NOTHING; END;
CREATE TRIGGER sync_keywords_d AFTER DELETE ON oferta_keywords BEGIN
  INSERT INTO sync_pendientes VALUES ('oferta_keywords', OLD.job_id, OLD.keyword) ON CONFLICT DO NOTHING; END;

CREATE TRIGGER sync_comb_i AFTER INSERT ON combinaciones BEGIN
  INSERT INTO sync_pendientes (tabla, k1) VALUES ('combinaciones', NEW.combinacion_id) ON CONFLICT DO NOTHING; END;
CREATE TRIGGER sync_comb_u AFTER UPDATE ON combinaciones BEGIN
  INSERT INTO sync_pendientes (tabla, k1) VALUES ('combinaciones', NEW.combinacion_id) ON CONFLICT DO NOTHING; END;
CREATE TRIGGER sync_comb_d AFTER DELETE ON combinaciones BEGIN
  INSERT INTO sync_pendientes (tabla, k1) VALUES ('combinaciones', OLD.combinacion_id) ON CONFLICT DO NOTHING; END;

CREATE TRIGGER sync_consultas_i AFTER INSERT ON consultas BEGIN
  INSERT INTO sync_pendientes (tabla, k1) VALUES ('consultas', NEW.consulta_id) ON CONFLICT DO NOTHING; END;
CREATE TRIGGER sync_consultas_u AFTER UPDATE ON consultas BEGIN
  INSERT INTO sync_pendientes (tabla, k1) VALUES ('consultas', NEW.consulta_id) ON CONFLICT DO NOTHING; END;

CREATE TRIGGER sync_hallazgos_i AFTER INSERT ON hallazgos BEGIN
  INSERT INTO sync_pendientes VALUES ('hallazgos', NEW.job_id, NEW.consulta_id) ON CONFLICT DO NOTHING; END;
CREATE TRIGGER sync_hallazgos_d AFTER DELETE ON hallazgos BEGIN
  INSERT INTO sync_pendientes VALUES ('hallazgos', OLD.job_id, OLD.consulta_id) ON CONFLICT DO NOTHING; END;

CREATE TRIGGER sync_eventos_i AFTER INSERT ON eventos BEGIN
  INSERT INTO sync_pendientes (tabla, k1) VALUES ('eventos', NEW.evento_id) ON CONFLICT DO NOTHING; END;
CREATE TRIGGER sync_eventos_u AFTER UPDATE ON eventos BEGIN
  INSERT INTO sync_pendientes (tabla, k1) VALUES ('eventos', NEW.evento_id) ON CONFLICT DO NOTHING; END;
