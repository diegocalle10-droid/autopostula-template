# F7 · Consulta libre (solo lectura)

## Propósito
Responder cualquier pregunta de **lectura** que no cubre otra skill: listas, recuentos, agrupaciones y búsquedas sobre ofertas y CV. Nunca escribe en la base.

## Disparadores
- «Muéstrame todas las ofertas que estén por revisar»
- «Hazme una tabla de las pendientes»
- «¿Cuántas vacantes hay en cada estado?»
- «¿Por qué motivos se descartaron?» / «agrupa las descartadas por motivo»
- «¿Qué empresas tienen ofertas aptas?»
- «Ofertas de Guatemala» / «¿de qué países son las aptas?»
- «Lo que entró esta semana»
- «Busca ofertas de Power BI»
- «¿Cuántos CV sin CV hay?» / «¿qué CV base se usa más?»

## Pasos

1. **Traduce la pregunta** con el glosario de `01_ORQUESTADOR.md` (por ejemplo «por revisar» → `estado = 'revisar'`).
2. **Usa la plantilla que encaje** y ajusta solo el filtro. Si ninguna encaja, escribe un `SELECT` siguiendo las reglas de abajo.
3. **Una sola consulta** que traiga todo lo necesario para responder.

## Reglas
- Solo `SELECT` (o `WITH … SELECT`). Nada que modifique datos.
- Pide solo las columnas que vas a mostrar; `descripcion` y `cv_md` solo si el usuario las pide.
- Listas: `ORDER BY` útil y `LIMIT 50`; si hay más, dilo y ofrece filtrar.
- Valores de la base en minúsculas y sin acentos: `pendiente`, `apta`, `revisar`, `descartada`; `sin_cv`, `redactada`, `rechazada`, `validada`.
- Fechas guardadas como texto ISO en UTC (`2026-10-30T12:00:00Z`): compara como texto.

## Plantillas

**Lista de un estado** (cambia `'revisar'` por el que pida):
```sql
SELECT job_id, empresa, titulo, pais, motivo_descarte, url FROM ofertas
WHERE estado = 'revisar' ORDER BY fecha_hallazgo DESC LIMIT 50;
```

**Recuento por estado** (ofertas y CV en una consulta):
```sql
SELECT 'oferta' AS tabla, estado, COUNT(*) AS total FROM ofertas GROUP BY estado
UNION ALL
SELECT 'cv', estado, COUNT(*) FROM emparejamientos GROUP BY estado
ORDER BY tabla, total DESC;
```

**Agrupar por motivo** (descartadas o revisar):
```sql
SELECT motivo_descarte, COUNT(*) AS total FROM ofertas WHERE estado = 'descartada'
GROUP BY motivo_descarte ORDER BY total DESC;
```

**Por país, empresa o fecha**:
```sql
SELECT pais, estado, COUNT(*) AS total FROM ofertas GROUP BY pais, estado ORDER BY pais, total DESC;
```
```sql
SELECT job_id, empresa, titulo, estado, fecha_hallazgo FROM ofertas
WHERE fecha_hallazgo >= to_char(now() AT TIME ZONE 'utc' - interval '7 days', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
ORDER BY fecha_hallazgo DESC LIMIT 50;
```

**Búsqueda por texto** (en título, empresa o descripción):
```sql
SELECT job_id, empresa, titulo, estado FROM ofertas
WHERE titulo ILIKE '%power bi%' OR empresa ILIKE '%power bi%' OR descripcion ILIKE '%power bi%'
ORDER BY fecha_hallazgo DESC LIMIT 50;
```

**CV por CV base**:
```sql
SELECT cv_id, estado, COUNT(*) AS total, ROUND(AVG(afinidad)) AS afinidad_media FROM emparejamientos
GROUP BY cv_id, estado ORDER BY cv_id, total DESC;
```

## Respuesta
Una línea con el resultado («12 ofertas por revisar») y una tabla con `ID` siempre como primera columna cuando son ofertas. Traduce los códigos a lenguaje claro cuando ayude (por ejemplo, `modalidad:hibrido` → «LinkedIn la rotula híbrida»). Si la lista lleva a una acción, sugiérela en una línea («para decidir, dime cuáles marco como aptas»).
