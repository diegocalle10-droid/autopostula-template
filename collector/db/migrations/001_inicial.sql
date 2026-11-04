-- Esquema inicial.
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

-- 7. PETICIONES EXTERNAS (hechas fuera del recolector; entran en el recuento diario)
CREATE TABLE peticiones_externas (
  externa_id    INTEGER PRIMARY KEY,
  ejecutada_en  TEXT    NOT NULL,
  tipo          TEXT    NOT NULL,
  cantidad      INTEGER NOT NULL,
  nota          TEXT,
  CHECK (tipo IN ('busqueda','detalle')),
  CHECK (cantidad > 0)
);
CREATE INDEX ix_externas_dia ON peticiones_externas (ejecutada_en);
