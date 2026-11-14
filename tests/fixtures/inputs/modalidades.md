# Modalidades de trabajo (parámetro de entrada)

Define qué modalidad se busca y cómo la rotula LinkedIn. Cambiar de remoto a híbrido es editar este archivo, no el código.

**La modalidad la da LinkedIn con la sesión de tu cuenta**, no la descripción: la búsqueda lleva el filtro de modalidad (`filtro`), que con sesión sí funciona, y cada tarjeta y cada oferta traen su etiqueta («En remoto», «Presencial», «Híbrido»). Si la etiqueta de una oferta no es de una modalidad aceptada, queda descartada con el motivo `modalidad:<nombre>` (regla `modalidad_no_aceptada` de `decisiones.md`). Si una oferta no trae etiqueta, vale la modalidad con la que se la buscó.

Reglas:
- **La primera modalidad con `aceptada = si` es la que se pide a LinkedIn** (con su `filtro`). Las demás aceptadas no multiplican las búsquedas: solo dejan de descartarse al leer su etiqueta.
- `filtro` es el valor del filtro de modalidad de LinkedIn: 1 presencial, 2 remoto, 3 híbrido.
- `etiquetas`: los rótulos con los que LinkedIn muestra esa modalidad, separados por comas. Se comparan sin mayúsculas ni acentos y deben coincidir con el rótulo entero; añade aquí los de otro idioma de la interfaz.

## Modalidades

| nombre | filtro | aceptada | etiquetas | senales |
|---|---|---|---|---|
| remoto | 2 | si | en remoto, remoto, remote | 100% remoto, 100 % remoto, 100% remote, totalmente remoto, completamente remoto, trabajo remoto, modalidad remota, modalidad remoto, fully remote, remote position, no presencial, sin presencialidad |
| hibrido | 3 | no | híbrido, hibrido, hybrid | hibrido, hibrida, hybrid, semipresencial, esquema mixto |
| presencial | 1 | no | presencial, on-site, onsite | presencial, on-site, onsite, on site, trabajo en oficina |
