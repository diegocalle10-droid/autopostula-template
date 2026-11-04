-- Cola de sincronización con la base online (Neon).
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

CREATE TRIGGER sync_externas_i AFTER INSERT ON peticiones_externas BEGIN
  INSERT INTO sync_pendientes (tabla, k1) VALUES ('peticiones_externas', NEW.externa_id) ON CONFLICT DO NOTHING; END;

-- Lo que ya existía también tiene que subir: la primera subida migra toda la base actual.
INSERT OR IGNORE INTO sync_pendientes (tabla, k1) SELECT 'ofertas', job_id FROM ofertas;
INSERT OR IGNORE INTO sync_pendientes SELECT 'oferta_keywords', job_id, keyword FROM oferta_keywords;
INSERT OR IGNORE INTO sync_pendientes (tabla, k1) SELECT 'combinaciones', combinacion_id FROM combinaciones;
INSERT OR IGNORE INTO sync_pendientes (tabla, k1) SELECT 'consultas', consulta_id FROM consultas;
INSERT OR IGNORE INTO sync_pendientes SELECT 'hallazgos', job_id, consulta_id FROM hallazgos;
INSERT OR IGNORE INTO sync_pendientes (tabla, k1) SELECT 'eventos', evento_id FROM eventos;
INSERT OR IGNORE INTO sync_pendientes (tabla, k1) SELECT 'peticiones_externas', externa_id FROM peticiones_externas;
