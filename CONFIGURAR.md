# CONFIGURAR — Entrevista de puesta en marcha

> Única fuente del guion de la entrevista. Lo sigue Claude (Claude Code en la web, claude.ai/code, o en tu ordenador) cuando escribes «configura mi Autopostula». Todo lo que se decide aquí acaba en `inputs/` y `CV/base/`, se sube a tu repositorio y desde ahí lo leen la captura, la rutina y el bot.

## 0. Reglas para Claude

- Eres quien entrevista. Habla en español, breve y claro, como con alguien que no es técnico. Haz **una pregunta o un bloque corto a la vez** y espera la respuesta.
- **No inventes datos del CV.** Todo dato personal, empresa, fecha, título o certificación sale del CV que da el usuario, copiado tal cual.
- Escribe solo en `inputs/`, `CV/base/`, `.github/workflows/cv-pdf.yml` (la línea del `cron`) y, para borrar el PDF, `CV/entrada/`. No toques el código.
- Respeta el formato de cada tabla de `inputs/` (columnas y cabeceras). Los ejemplos de formato completos están en `tests/fixtures/inputs/`.
- Si el usuario ya configuró antes (hay filas en `inputs/cv.md`, `inputs/puestos.md` o `inputs/ubicaciones.md`), enséñale un resumen y pregúntale qué parte quiere cambiar; haz solo esa.
- Antes del primer comando, instala las dependencias: `pip install -r requirements.txt`.
- **Parámetros de la entrevista** (solo los usa este guion):

  | clave | valor | qué significa |
  |---|---|---|
  | exhaustividad_prefiltro | alta | Al generar las familias del título (paso 2): cada familia positiva con al menos 15 raíces, en español e inglés, con sinónimos, abreviaturas y nombres de herramientas; y familias negativas para cada área vecina que se cuele. Mejor pasarse que quedarse corto: una oferta que no pasa el prefiltro nunca llega |
  | titulos_prueba_relevantes | 20 | Títulos que el usuario querría ver y que deben pasar `probar-titulos` |
  | titulos_prueba_ajenos | 10 | Títulos parecidos pero ajenos que deben quedar fuera |

- **Reglas fijas que no se preguntan:** solo ofertas con solicitud sencilla (Easy Apply) y solo ofertas abiertas.

## 1. Tu CV

1. Pide el CV en PDF: «Adjúntalo aquí en el chat». Si no se puede adjuntar, que lo suba desde GitHub a `CV/entrada/` (Add file → Upload files) y te avise; entonces haz `git pull`.
2. Pregunta si quiere **uno o varios perfiles** (por ejemplo, «analista de datos» y «operaciones»). Cada perfil es un CV base distinto: el mismo historial contado con otro foco. Si solo tiene un CV, un perfil.
3. Convierte cada perfil a Markdown en `CV/base/<id>.md`, **en español** (en esta versión la validación solo reconoce las secciones en español; si el PDF está en otro idioma, tradúcelo sin cambiar ningún dato), con **exactamente** la estructura y los títulos de sección de `configurar/cv_ejemplo.md`:
   - `# NOMBRE COMPLETO`, debajo la línea de título y la línea de contacto (teléfono · correo · LinkedIn, separados por `·`).
   - `## PERFIL PROFESIONAL`, `## EXPERIENCIA PROFESIONAL` con cada puesto como `### Cargo` y, en la línea siguiente, `Empresa — Ciudad, País | Mes Año – Mes Año`; los logros con `- `.
   - `## FORMACIÓN` (una línea por título), `## CERTIFICACIONES` (`- ` por certificación), `## STACK TÉCNICO` (`- **Grupo:** a · b`) y la línea `**Idiomas:** español (nativo) · inglés B2`.
4. Rellena la tabla «CV base» de `inputs/cv.md`: `id` (en minúsculas y con `_`), `archivo` (`CV/base/<id>.md`), `perfil` y una `nota` con lo que lo distingue. `umbral_afinidad` se queda en 35 salvo que pida otra cosa.
5. Ejecuta `python cli.py validar-cv`. Si algo falla, corrígelo y repite. Enséñale el resumen (nombre, correo, puestos, estudios, idiomas) y pídele que confirme que es correcto.
6. Si subió el PDF a `CV/entrada/`, bórralo del repositorio (`git rm`).

## 2. Puestos que buscas

1. Pregunta qué puestos quiere buscar, con sus palabras. Ayúdale a convertirlos en **términos de búsqueda cortos**, uno por fila, sin `OR` ni paréntesis (por ejemplo, «analista de datos», «data analyst», «power bi»). Si busca en dos idiomas, cada variante es otra fila.
2. Prioridad 1 para lo principal, 2 para lo secundario. Escribe la tabla «Términos» de `inputs/puestos.md`.
3. Con esos puestos y su CV, **genera las familias del título** de `inputs/prefiltro.md` según `exhaustividad_prefiltro` (mira el formato y la amplitud de `tests/fixtures/inputs/prefiltro.md`):
   - Familias positivas (peso 3 lo central, 2 lo cercano) con raíces en español e inglés; `palabra*` cubre variantes.
   - Familias negativas (de -2 a -4) para las áreas que suelen colarse con las mismas palabras y no son su perfil (por ejemplo marketing o ventas para un analista).
   - Explícale en dos líneas para qué sirve: decide a qué ofertas se les pide el detalle.
4. **Compruébalo:** escribe `titulos_prueba_relevantes` títulos reales que querría ver (varios idiomas, niveles y formas de escribirlos) y `titulos_prueba_ajenos` que no, y pásalos por `python cli.py probar-titulos "título 1" "título 2" …`. Todos los relevantes deben salir `PASA` y los ajenos `FUERA`; si no, amplía raíces o familias y repite. Enséñale el resultado final.

## 3. Dónde buscas

1. Pregunta en qué lugares: países, regiones o ciudades (por ejemplo, «solo Madrid», «toda España», «Canarias», «Latinoamérica»). No hay ninguno por defecto.
2. Escribe la tabla «Lugares» de `inputs/ubicaciones.md`: `frase` con el nombre que entiende LinkedIn (en inglés si hay duda: `Spain`, `Canary Islands`, `Mexico`), `tipo` y `pais_esperado` (el país como aparece en LinkedIn; `-` en una región de varios países).
3. «Países aceptados»: los países donde acepta trabajar (al menos los de sus lugares), con `prioridad_detalle` 1. Si busca en una región amplia, pregunta si hay países de esa región que no le valen y ponlos en «Países excluidos».

## 4. Modalidad

Pregunta si busca **remoto, híbrido o presencial** (puede ser más de uno). En `inputs/modalidades.md`, `aceptada` = `si` en las elegidas y `no` en las demás. Pon primera la que más le interesa.

## 5. Idiomas

1. **Idioma propio**: en qué idioma quiere trabajar, español (`es`) o inglés (`en`). Sirve para filtrar ofertas; sus CV se redactan en español en esta versión.
2. **El otro idioma** (inglés si el propio es español, y al revés): pregunta qué hacer con las ofertas que exigen un nivel alto de ese idioma:
   - **Descartarlas** (no lo domina): `idioma_vigilado` = ese idioma y se dejan las reglas de idioma de `inputs/decisiones.md` como están.
   - **Aceptarlas** (lo domina): `idioma_vigilado` = ese idioma igualmente, pero en `inputs/decisiones.md` las reglas `nivel_exigente`, `nivel_dudoso`, `contenido_vigilado_titulo_no`, `contenido_vigilado_nivel_aceptable` y `contenido_vigilado` pasan a estado `apta` con motivo vacío.
   - **Revisarlas una a una**: esas mismas reglas pasan a `revisar` con su motivo.
3. En `inputs/idioma.md` pon `idioma_propio` e `idioma_vigilado`, y sustituye las secciones «Alias del idioma vigilado», «Pasa» y «Rechaza» por las de `configurar/idioma_vigilado_<código>.md`.

## 6. Horarios

1. **Zona horaria** (por ejemplo `Europe/Madrid`, `America/Bogota`): `zona_horaria` en `inputs/mensajes/parametros.md`.
2. **Hora de la rutina de CV** (recomendada las 06:00 de su zona: así los CV están en Telegram al despertar): `hora_rutina` en `inputs/mensajes/enlaces.md`, con su zona (`06:00 (hora de Madrid)`).
3. **Horas de cada captura**: la lanzará al irse a dormir y tiene que terminar antes de la rutina. Ejemplo: si se acuesta a las 23:00 y la rutina es a las 06:00, como mucho 6. Ponlo en `horas_por_defecto` de `inputs/lotes.md`. El PC se apaga solo 25 minutos después de terminar.

## 7. Enlaces

- `repo_github` en `inputs/mensajes/enlaces.md`: el repositorio de esta sesión, como `usuario/repo` (de `git remote get-url origin`, quitando lo que no sea `usuario/repo`).
- `neon_project_id`, `url_consola_neon` y `url_rutina` se quedan en `PENDIENTE`: los rellena la instalación en el PC (`INSTALAR.md`). Mientras tanto los mensajes de Telegram muestran «PENDIENTE» en su lugar. Díselo.

## 8. Comprobar y subir

1. Ejecuta `python cli.py validar-cv`, `python -m unittest discover -s tests` y `python tools/check_size.py`. Todo debe pasar.
2. Haz commit («Configuración inicial») y súbelo a `main`. Si la sesión trabaja en otra rama, abre un pull request y pídele que lo fusione.
3. Termina con un resumen corto de lo configurado y el siguiente paso, tal cual:
   > Ahora, en tu ordenador con Windows: abre la app de escritorio de Claude → pestaña **Code** → elige una carpeta vacía (por ejemplo `Documentos\Autopostula`) y escribe: «Clona https://github.com/<repo_github> aquí y sigue INSTALAR.md». Claude comprobará lo que falta, lo instalará contigo y dejará todo funcionando.
