-- Esquema online (Neon / PostgreSQL), la única base oficial. Mismos campos y CHECK que la SQLite local (001_inicial.sql);
-- fechas como TEXT ISO UTC y ids enteros que vienen del local (sin identity). `emparejamientos` y `avisos` viven solo aquí.

-- Una fila por vacante. La escribe el PC de captura (subida desde SQLite); el bot (F2) cambia estado y revisada_en, y con
-- revisada_en informada la subida ya no toca la fila.
CREATE TABLE ofertas (
  job_id TEXT PRIMARY KEY, url TEXT NOT NULL, titulo TEXT NOT NULL, empresa TEXT, ubicacion TEXT, pais TEXT,
  fecha_publicacion TEXT, fecha_hallazgo TEXT NOT NULL, ultima_vista TEXT NOT NULL,
  descripcion TEXT, detalle_obtenido_en TEXT, tipo_empleo TEXT, activa INTEGER,
  modalidad TEXT NOT NULL, modalidad_detectada TEXT,
  idioma_titulo TEXT, idioma_contenido TEXT, nivel_idioma TEXT,
  estado TEXT NOT NULL DEFAULT 'pendiente', motivo_descarte TEXT, huella TEXT,
  duplicada_de TEXT REFERENCES ofertas(job_id), revisada_en TEXT,
  CHECK (estado IN ('pendiente','apta','revisar','descartada')),
  CHECK (activa IS NULL OR activa IN (0,1)),
  CHECK (nivel_idioma IS NULL OR nivel_idioma IN ('ninguno','aceptable','exigente','dudoso')),
  CHECK (estado <> 'descartada' OR motivo_descarte IS NOT NULL)
);
CREATE INDEX ix_ofertas_huella ON ofertas (huella);
CREATE INDEX ix_ofertas_estado ON ofertas (estado);
CREATE INDEX ix_ofertas_hallazgo ON ofertas (fecha_hallazgo);

-- Términos de puestos.md hallados en cada descripción. PC de captura.
CREATE TABLE oferta_keywords (
  job_id TEXT NOT NULL REFERENCES ofertas(job_id) ON DELETE CASCADE, keyword TEXT NOT NULL,
  PRIMARY KEY (job_id, keyword)
);
CREATE INDEX ix_keywords_keyword ON oferta_keywords (keyword);

-- Réplica de la captura (PC de captura, vía la cola sync_pendientes de SQLite): agenda término × ubicación, cada petición
-- de búsqueda, qué consulta halló qué oferta e incidentes del disyuntor.
CREATE TABLE combinaciones (
  combinacion_id BIGINT PRIMARY KEY, termino TEXT NOT NULL, ubicacion_frase TEXT NOT NULL,
  prioridad INTEGER NOT NULL, cadencia_dias INTEGER NOT NULL, ultima_ejecucion TEXT, proxima_ejecucion TEXT,
  pasadas_sin_nuevas INTEGER NOT NULL DEFAULT 0, activa INTEGER NOT NULL DEFAULT 1,
  UNIQUE (termino, ubicacion_frase),
  CHECK (prioridad >= 1), CHECK (cadencia_dias >= 1), CHECK (activa IN (0,1))
);

CREATE TABLE consultas (
  consulta_id BIGINT PRIMARY KEY, combinacion_id BIGINT NOT NULL REFERENCES combinaciones(combinacion_id),
  pagina INTEGER NOT NULL DEFAULT 1, jobage_dias INTEGER NOT NULL, ejecutada_en TEXT NOT NULL,
  resultado TEXT NOT NULL, n_resultados INTEGER, n_nuevos INTEGER, codigo_error TEXT,
  CHECK (resultado IN ('ok','vacia','fallida','desafio')), CHECK (pagina >= 1)
);
CREATE INDEX ix_consultas_dia ON consultas (ejecutada_en);
CREATE INDEX ix_consultas_comb ON consultas (combinacion_id, ejecutada_en);

CREATE TABLE hallazgos (
  job_id TEXT NOT NULL REFERENCES ofertas(job_id) ON DELETE CASCADE,
  consulta_id BIGINT NOT NULL REFERENCES consultas(consulta_id),
  PRIMARY KEY (job_id, consulta_id)
);

CREATE TABLE eventos (
  evento_id BIGINT PRIMARY KEY, ocurrido_en TEXT NOT NULL, tipo TEXT NOT NULL, contexto TEXT, pausa_hasta TEXT,
  CHECK (tipo IN ('429','vacios_repetidos','fallo'))
);

-- CV a medida. Lo escriben la rutina de la nube y el bot (F1, F3, F6); lo valida la Action `CV a PDF`.
-- sin_cv -> nada encaja | redactada -> espera validación | rechazada -> falló la validación (se reintenta)
-- validada -> pasó, PDF generado y enviado por Telegram
CREATE TABLE emparejamientos (
  job_id TEXT PRIMARY KEY REFERENCES ofertas(job_id) ON DELETE CASCADE,
  estado TEXT NOT NULL, cv_id TEXT, afinidad INTEGER, requisitos_cubiertos TEXT, requisitos_faltantes TEXT,
  motivo TEXT, cv_md TEXT, rechazo TEXT, intentos INTEGER NOT NULL DEFAULT 0,
  emparejado_en TEXT NOT NULL, validado_en TEXT, notificado_en TEXT,
  CHECK (estado IN ('sin_cv','redactada','rechazada','validada')),
  CHECK (afinidad IS NULL OR afinidad BETWEEN 0 AND 100),
  CHECK (estado <> 'sin_cv' OR motivo IS NOT NULL),
  CHECK (estado = 'sin_cv' OR (cv_id IS NOT NULL AND afinidad IS NOT NULL AND cv_md IS NOT NULL))
);
CREATE INDEX ix_emparejamientos_estado ON emparejamientos (estado);

-- Ofertas por redactar: aptas (y solo aptas) sin emparejamiento, más las rechazadas con menos de 3 intentos
-- (regla fija: la misma cifra es INTENTOS_MAXIMOS en collector/online/pdfs.py).
CREATE VIEW ofertas_por_redactar AS
SELECT o.job_id, o.titulo, o.empresa, o.ubicacion, o.pais, o.modalidad, o.url, o.descripcion,
       e.rechazo, COALESCE(e.intentos, 0) AS intentos
FROM ofertas o LEFT JOIN emparejamientos e ON e.job_id = o.job_id
WHERE (o.estado = 'apta' AND e.job_id IS NULL) OR (e.estado = 'rechazada' AND e.intentos < 3);
