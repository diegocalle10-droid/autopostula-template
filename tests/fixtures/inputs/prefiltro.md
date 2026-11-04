# Prefiltro de detalle (parámetro de entrada)

El detalle es la petición más escasa (una por oferta) y la que decide si se postula. Antes de pedirlo, el título de cada oferta se puntúa con las **familias del título**. Si alcanza `puntuacion_minima`, se pide su detalle y las reglas de `decisiones.md` deciden con la descripción completa (idioma, modalidad…). Si no la alcanza, la oferta queda **descartada** con el motivo `titulo_fuera_de_perfil:<familia>` (la familia negativa de más peso, o `sin_familia` si no aparece ninguna).

El filtro se aplica al entrar cada oferta y, al arrancar `run-continuo`, `detail` o `plan`, a las que sigan pendientes de detalle (por ejemplo, si cambias esta tabla).

Una oferta es **elegible** para el detalle si cumple todo:
1. Su país es uno de **Países aceptados** (`ubicaciones.md`) y está confirmado, salvo que la regla de ingreso `pais_desconocido` de `decisiones.md` sea `evaluar`.
2. Su título alcanza `puntuacion_minima`.
3. No es duplicada ni de un país excluido (eso ya se filtra al recolectar).

Las elegibles se ordenan según la tabla **Orden del detalle**.

## Reglas

| clave | valor | nota |
|---|---|---|
| puntuacion_minima | 1 | Puntos mínimos del título para pedir su detalle |
| prioridad_pais_por_defecto | 1 | Prioridad de un país aceptado sin valor en `ubicaciones.md` |

## Orden del detalle

Criterios en orden de importancia; el primero manda y los siguientes desempatan. Criterios disponibles: `prioridad_pais` (1 = primero, se define en `ubicaciones.md`), `puntos` (puntuación del título) y `recencia` (fecha de publicación). `asc` pone primero el valor menor; `desc`, el mayor.

| criterio | sentido |
|---|---|
| prioridad_pais | asc |
| puntos | desc |
| recencia | desc |

## Familias del título

Cada familia que aparece en el título suma su `peso` **una sola vez**, aunque coincidan varias de sus raíces; la suma es la puntuación. Peso positivo: acerca el título al perfil. Negativo: lo aleja (un título de marketing con «analytics» no pasa).

Cómo se escriben las `raices` (separadas por comas; se comparan sin mayúsculas ni acentos, con los signos de puntuación como espacios):
- `dato*` con asterisco: cualquier palabra que **empiece** así (datos, dato). Cubre plurales, género y variantes sin escribirlas.
- `bi` sin asterisco: la palabra o la frase **exacta** (`bi` no casa con «bilingual»; `supply chain`, solo esa frase).

Para adaptar el filtro a otro perfil basta con cambiar las familias: no hace falta escribir cada puesto. Las palabras de nivel o modalidad (intern, junior, senior, remote) no puntúan a propósito: que el detalle decida.

| familia | peso | raices | nota |
|---|---|---|---|
| datos | 3 | dato*, data, database*, big data, master data, data master, datos maestros, maestro de datos, sql, etl, elt, dwh, data warehouse, data lake, lakehouse, gobierno del dato, gobernanza del dato, data governance, calidad del dato, data quality, modelado de datos, data model*, base de datos, bases de datos, dba, mdm | Bases de datos, calidad y gobierno del dato |
| bi_analitica | 3 | bi, business intelligence, inteligencia de negocio*, inteligencia mediatica, analitic*, analytic*, metrica*, metric*, indicador*, kpi*, report*, dashboard*, cuadro de mando, tablero*, power bi, tableau, looker, qlik, visualizacion*, visualization, insight*, estadistic*, statistic*, cuantitativ*, quantitative | Reporting, cuadros de mando, métricas |
| ia_ciencia | 3 | ia, ai, inteligencia artificial, artificial intelligence, machine learning, ml, deep learning, llm*, genai, gen ai, ia generativa, generative ai, agente* de ia, ai agent*, cientifico*, cientifica*, scientist*, data science, ciencia de datos, modeler, modelador*, modeling, modelado, predictiv*, predictive, nlp, prompt*, decision science, chatbot*, conversational ai, ia conversacional | IA aplicada y ciencia de datos |
| procesos | 3 | proceso*, process*, mejora continua, continuous improvement, kaizen, lean, six sigma, seis sigma, reingenieria, reengineering, bpm, optimizacion*, optimization, eficiencia, efficiency, transformacion digital, digital transformation, organizacion digital, ingenier* industrial, industrial engineer* | Mejora continua, reingeniería, ingeniería industrial |
| automatizacion | 3 | automatiz*, automation*, automated, rpa, power automate, power platform, power apps, n8n, make.com, zapier, uipath, blue prism, workflow*, low code, no code, integracion*, integration*, api, apis, copilot studio, copilot | Automatización e integraciones |
| operaciones | 2 | operacion*, operation*, ops, revops, service management, gestion de servicio*, pmo, project management office, planificacion operativa, coordinador de operaciones, operations analyst | Operaciones y gestión de servicio |
| cadena_suministro | 2 | supply chain, cadena de suministro, cadena de abastecimiento, abastecimiento, inventario*, inventor*, stock, almacen*, warehouse, logistic*, logistica*, distribucion, distribution, ruta*, routing, demand planning, planificacion de la demanda, planeacion de la demanda, forecast*, pronostico*, s&op, procurement, compra*, purchasing, sourcing, materiales, materials, merchandising, planograma*, modular*, asset management, gestion de activos, mrp | Logística, inventario, compras, planificación |
| control_calidad | 2 | auditor*, auditoria*, audit, compliance, cumplimiento, control interno, internal control*, controls, riesgo*, risk, calidad, quality, qa, aseguramiento, iso, record to report, r2r, estados financieros, planificacion y analisis financiero, fp&a, sostenibilidad, sustainability, esg, lca | Auditoría, cumplimiento, calidad, control |
| sistemas_negocio | 2 | erp, sap, oracle, netsuite, dynamics, salesforce, crm analyst, workday, sharepoint, microsoft 365, m365, office 365, analista funcional, functional analyst, business analyst, analista de negocio*, consultor funcional, architect*, arquitect*, technical analyst, analista tecnico, application support, soporte de aplicaciones, customer success, search relevancy, revenue operations, sistemas de informacion, information system*, requerimiento*, requirement*, documentacion tecnica, technical documentation, crm sr analyst, crm senior analyst, analista crm | ERP, CRM y análisis funcional |
| marketing | -4 | marketing, mercadeo, ads, advertising, publicidad, paid, ppc, sem, seo, social, social media, redes sociales, community manager, media, medios, estratega de medios, copywriter*, brand*, marca, trade marketing, growth, performance marketing, funnel | Marketing, medios, publicidad |
| ventas_comercial | -2 | ventas, sales, venta, vendedor*, account manager, account executive, ejecutivo de cuenta*, ejecutivo comercial, asesor comercial, coordinador comercial, analista comercial, planner comercial, planeacion comercial, planificacion comercial, planeamiento comercial, estrategia comercial, inteligencia comercial, market intelligence, marketing intelligence, pricing, precio*, revenue management, net revenue, rgm, segmento, business development, desarrollo de negocio*, preventa, telemarketing | Ventas, comercial, precios |
| finanzas_contabilidad | -3 | credito*, credit, cobranza*, collections, tesoreria, treasury, contable, contabilidad, accounting, accountant, contador*, analista financiero, financial analyst, finance analyst, finance manager, commercial finance, financial planning, impuestos, tax, nomina*, payroll, facturacion, billing, cartera de credito | Finanzas puras, contabilidad, crédito |
| rrhh_atencion | -4 | recursos humanos, human resources, rrhh, hr, hris, talento, talent, reclutador*, recruiter*, seleccion de personal, workforce, wfm, real time analyst, call center, contact center, customer experience, customer service, atencion al cliente, servicio al cliente, soporte tecnico nivel | RR. HH., atención al cliente, planificación de plantilla |
| fuera_de_perfil | -4 | ux, ui, diseñador*, disenador*, designer*, product owner, scrum master, devops, sre, platform engineer, dynatrace, economics, economist*, market logic, decisiones- fico, fico, desarrollo rural, vending, chofer, conductor, driver, mecanico*, enfermer*, medico*, docente, profesor*, abogad*, legal, oficial de control, general manager, gerente general | Diseño, producto y otros oficios ajenos |
