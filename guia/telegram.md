# Telegram: el bot que te envía los CV

Cada mañana te llega un mensaje por oferta, con el CV en PDF y el enlace para postularte. Lo envía un bot tuyo que solo te escribe a ti.

1. En Telegram, busca **@BotFather** (con la marca azul de verificado) y ábrelo.
   ![BotFather en el buscador](img/telegram-01.png) *(captura pendiente)*
2. Escribe `/newbot`. Te pide un **nombre** (el que verás, por ejemplo «Mis CV») y un **usuario** que termine en `bot` (por ejemplo `micv_autopostula_bot`).
   ![Conversación con BotFather](img/telegram-02.png) *(captura pendiente)*
3. BotFather te responde con un **token** (números, dos puntos y letras). Es secreto: pégalo en tu `.env`, en `TELEGRAM_BOT_TOKEN=`, y guarda.
   ![Mensaje con el token](img/telegram-03.png) *(captura pendiente)*
4. Pulsa el enlace a tu bot (`t.me/<usuario>`), dale a **Iniciar** y escríbele cualquier cosa («hola»).
   ![Chat con tu bot](img/telegram-04.png) *(captura pendiente)*
5. Claude ejecuta `python cli.py telegram-chat-id`: muestra tu `TELEGRAM_CHAT_ID` y lo pone en el `.env`.
