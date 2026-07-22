# Feature: Integración de órdenes de Batalla Territorial (BT) desde MongoDB

## Descripción

Integrar en Sonda Droid la capacidad de publicar órdenes de Batalla Territorial (BT)
almacenadas en MongoDB en un canal de Discord, siguiendo el mismo patrón que el
Telegram Bot Darjetii (`Bot-Darjetii/modules/mongo.py`).

## Motivación

La guild necesita que las órdenes de BT se publiquen tanto en Telegram como en Discord.
Actualmente el Telegram bot ya lo hace; este cambio extiende Sonda Droid para cubrir
Discord con la misma lógica.

## Requisitos funcionales

1. **Conexión a MongoDB** — Leer órdenes activas desde la misma colección `orders`
   que usa el Telegram bot, usando los mismos `template_id` por fase:
   - Fase 1 → `ordenes_fase_1`
   - Fase 2 → `ordenes_fase_2`
   - Fase 3 → `ordenes_fase_3`
   - Fase 4 → `ordenes_fase_4`
   - Fase 5 → `ordenes_fase_5_mandalore`
   - Fase 6 → `ordenes_fase_6_mandalore`

2. **Configuración de fecha de BT** — Comando `!set_bt_date YYYY-MM-DD` (solo admins)
   para establecer el lunes de inicio de la BT. Almacenado en SQLite (`bt_config`).

3. **Publicación automática diaria** — A las 17:00 UTC, calcular la fase actual
   basada en la fecha de inicio y publicar la orden correspondiente en el canal
   `#ordenes-bt` (`GUILD_ORDERS_CHANNEL_ID`).

4. **Publicación manual** — Comando `!orden <1-6>` (solo admins) para forzar la
   publicación de una fase específica.

5. **Formato** — Usar el mismo formato que el Telegram bot:
   "LUNES 6 de Julio:\n\n{contenido}" con embed de Discord.

6. **Estado** — `!estado` debe mostrar el estado de BT (inicio, fase actual).

## Cambios necesarios

| Archivo | Cambio |
|---------|--------|
| `bot.py` | Añadir conexión MongoDB, BT date, scheduled task, comandos `!set_bt_date` y `!orden`, mejorar `!estado` |
| `pyproject.toml` | Añadir dependencia `pymongo` |
| `.env` | Añadir `GUILD_ORDERS_CHANNEL_ID`, `ADMIN_IDS`, `MONGODB_URI`, `MONGODB_DB_NAME` |
| `.env.example` | Documentar las nuevas variables |

## Referencias

- `Bot-Darjetii/modules/mongo.py` — Singleton de MongoDB y `get_template_order()`
- `Bot-Darjetii/modules/scheduler.py` — `send_daily_reminder()` a las 17:00 UTC
- `Bot-Darjetii/bot.py` — `/iniciar_bt` command, `random_message`
- `Bot-Darjetii/modules/database.py` — `set_bt_start_date()`, `get_bt_start_date()`
