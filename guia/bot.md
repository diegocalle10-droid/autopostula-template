# Bot de gestión (opcional)

Un Project de claude.ai para manejar tus ofertas hablando, desde el móvil o el ordenador: «¿qué tengo pendiente?», «marca la 4012 como apta», «genérame el CV de esta oferta», «reenvíame el PDF». Los pasos técnicos completos están en `skills-project-bot/LEEME.md`; aquí, dónde se hace cada uno.

Antes: el conector de Neon (`guia/conector-neon.md`).

1. claude.ai → **Projects** → **Crear proyecto** → nombre «Autopostula».
   ![Crear Project](img/bot-01.png) *(captura pendiente)*
2. **Instrucciones** → Editar: pega solo la frase de `skills-project-bot/LEEME.md` (paso 2).
   ![Instrucciones del Project](img/bot-02.png) *(captura pendiente)*
3. **Contexto** (o Conocimiento) → **Agregar** → **GitHub** → tu repositorio, rama `main` → marca los archivos que indica `skills-project-bot/LEEME.md` (paso 3).
   ![Archivos de GitHub en el contexto](img/bot-03.png) *(captura pendiente)*
4. En el chat del Project, activa los conectores **Neon** y **GitHub**.
5. Prueba: «¿Qué tengo pendiente?». Debe responder con datos de tu base.
   ![Primera respuesta del bot](img/bot-04.png) *(captura pendiente)*
