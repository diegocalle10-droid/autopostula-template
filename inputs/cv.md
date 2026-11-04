# CV a medida por oferta (parámetro de entrada)

Cada CV base es una fuente de verdad independiente: cuenta su propia historia y no hace falta que coincida con los demás. Las rutas son relativas a la raíz del proyecto.

## CV base

| id | archivo | perfil | nota |
|---|---|---|---|

## Reglas

| clave | valor | nota |
|---|---|---|
| umbral_afinidad | 35 | % mínimo de requisitos de la oferta cubiertos por el mejor CV. Por debajo, la oferta queda `sin_cv` con su motivo. Lo aplica la rutina de la nube leyendo este archivo, no el código |
| tope_rutina | 30 | Ofertas que la rutina redacta como mucho por ejecución (el resto, en la siguiente). Lo aplica la rutina leyendo este archivo; el resumen de Telegram lo cita |
