# Bot de gestión (opcional)

Un Project de Claude para manejar tus ofertas hablando, desde el móvil o el ordenador: «¿qué tengo pendiente?», «marca la 4012 como apta», «genérame el CV de esta oferta», «reenvíame el PDF». Qué archivo va en cada sitio: `skills-project-bot/LEEME.md`; aquí, dónde hacer clic.

Antes: el conector de Neon (`guia/conector-neon.md`) y tener el repositorio al día en GitHub.

## 1. Crear el Project

1. En el menú de la izquierda, entra en **Proyectos** y pulsa **+** (1), o **Nuevo proyecto**.

   ![Menú: Proyectos y el botón de crear proyecto](img/bot-01.png)

2. Ponle nombre `Autopostula_Neon_Bot` (1) y pulsa **Crear proyecto** (2). El resto es opcional.

   ![Crear un proyecto](img/bot-02.png)

## 2. Instrucciones

1. En el Project, pulsa **Editar** (1) en **Instrucciones**.

   ![Project: Instrucciones → Editar](img/bot-03.png)

2. Pega solo la frase de `skills-project-bot/LEEME.md` (paso 2) y pulsa **Guardar instrucciones**.

   ![Establecer instrucciones del proyecto](img/bot-04.png)

## 3. Contexto: los archivos del bot

1. En **Contexto**, pulsa **Agregar**.

   ![Project: Contexto → Agregar](img/bot-05.png)

2. Elige **GitHub**.

   ![Menú Agregar: GitHub](img/bot-06.png)

3. Elige tu repositorio (1) y entra en la carpeta `skills-project-bot`. Marca `00_SYSTEM_PROMPT.md` (2), `01_ORQUESTADOR.md` y `F1` … `F7`: 9 archivos (en la captura falta marcar el `00_SYSTEM_PROMPT.md`). `LEEME.md` no hace falta. Pulsa **Agregar archivos** (3).

   ![Agregar contenido desde GitHub](img/bot-07.png)

4. En el Contexto aparece tu repositorio, sincronizado desde GitHub.

   ![Contexto con el repositorio enlazado](img/bot-08.png)

## 4. Conectores

En el chat del Project, activa los conectores **NEON_MCP** y **GitHub** (en el menú **+** de la caja de mensaje).

## 5. Prueba

Pregunta «¿Qué tengo pendiente?». Debe responder con los recuentos de tu base y la lista de lo que necesita tu decisión.

![Primera respuesta del bot: recuentos](img/bot-09.png)

*(La captura es de otra instalación: tus números serán los tuyos.)*
