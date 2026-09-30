# ClassicForever_Bots

Panel del cliente para los bots de mazmorra del servidor (`.dungeonbots`, `src/server/game/Bots/DungeonBots1601.cpp`).
Español e inglés (según el cliente, o `/bots lang es|en|auto`). Estética del launcher: cuero, bordes dorados y logo.

Instalar: lo instala y actualiza el launcher (Opciones → Addons del servidor). A mano: copiar la carpeta
`ClassicForever_Bots` a `_classic_beta_/Interface/AddOns/`.

## Qué hace

| En el panel | Comando que manda | Necesita |
|---|---|---|
| Mazmorra (automática dentro de una, o elegida) + Tu rol (automático o tanque/sanador/DPS) → **Llenar grupo** | `.dungeonbots <rfc\|deadmines\|rol\|wc\|sfk\|bfd> [tank\|healer\|dps]` | ya existía |
| **Empezar**, **Parar**, **Seguirme**, **Esperar aquí**, **Atraer**, **Descansar** | `.dungeonbots start\|stop\|follow\|wait\|pull\|rest` | parche `dbot-orders` en el servidor |
| **Atacar mi objetivo**, **Tirar mi objetivo** | `.dungeonbots attack\|pulltarget` | parche `dbot-orders` |
| **Saltar paso**, **Volver a la entrada** | `.dungeonbots skip\|back` | parche `dbot-orders` |
| Panel **Grupo**: paso de la ruta, orden activa, combate, objetivo y barras de vida y maná de cada bot | `.dungeonbots watch on` (lo pide solo) | parche `dbot-orders` |
| **Estado** | `.dungeonbots status` | ya existía |
| **Despedir** (con confirmación) | `.dungeonbots dismiss` | ya existía |

Marcas de banda (parche `dbot-orders`): calavera y después cruz = orden de muerte; luna = el mago bot le pone la oveja
y nadie la pega.

El servidor elige solo la variante de tu facción (`deadmines` → `deadmines_h`, `wc` → `wc_a`...). La línea de abajo del
panel muestra la respuesta del servidor a la última orden. El estado en vivo llega como mensajes de sistema que
empiezan por `[CFB]`: el addon los oculta del chat y el servidor solo los manda a quien los pide.

Además:
- se abre solo al entrar en una mazmorra con preset (se puede quitar en Ajustes);
- atajos de teclado (Menú → Atajos de teclado → Classic Forever: Bots de mazmorra) para abrir el panel y cada orden;
- `/bots`, `/bots fill [mazmorra] [rol]`, `/bots start|stop|follow|wait|pull|rest|attack|pulltarget|skip|back|status|dismiss`, `/bots lang`;
- Ajustes: transparencia, tamaño, abrir al entrar, botón del minimapa (se arrastra alrededor), bloquear la ventana;
- solo el líder del grupo manda órdenes (el servidor lo comprueba también); Escape cierra el panel.

## Ideas anotadas (no hechas)

- Que ciertos bots no tiren NEED: **descartado** a propósito (evita abusar de los bots para el botín).
- Control con marcas más allá de la oveja: sap del pícaro, destierro, trampa de hielo (hoy solo el mago y la luna).
