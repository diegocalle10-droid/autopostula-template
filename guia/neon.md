# Neon: tu base de datos

Neon guarda en la nube las ofertas, su estado y los CV. El plan gratuito basta.

1. Entra en **neon.tech** → **Sign up** (con tu cuenta de GitHub o tu email).
   ![Registro en Neon](img/neon-01.png) *(captura pendiente)*
2. Crea un proyecto: nombre `autopostula`, la versión de Postgres que venga por defecto y la **región** más cercana a ti (por ejemplo, Frankfurt si estás en Europa).
   ![Crear proyecto](img/neon-02.png) *(captura pendiente)*
3. En el panel del proyecto, pulsa **Connect**. Deja la base `neondb` y copia la **cadena de conexión** (empieza por `postgresql://`). Es secreta: no la compartas.
   ![Botón Connect y cadena de conexión](img/neon-03.png) *(captura pendiente)*
4. Pégala en tu `.env`, en la línea `NEON_DATABASE_URL=` (Claude te abre el archivo con el Bloc de notas). Guarda.
5. Ve a **Settings → General** y copia el **Project ID** (algo como `palabra-palabra-12345678`). Este no es secreto: díselo a Claude.
   ![Project ID en Settings](img/neon-04.png) *(captura pendiente)*

Claude crea las tablas con `python cli.py instalar`; tú no tienes que tocar nada más en Neon.
