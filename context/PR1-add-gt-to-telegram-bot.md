# PR 1: Añadir soporte de Guerra Territorial (GT) al Telegram Bot

## Contexto

El bot Darjetii actualmente solo publica órdenes de BT (Batalla Territorial) automáticamente a
las 17:00 UTC. La GT (Guerra Territorial) tiene una estructura similar pero con 4 fases en
lugar de 6:

| Fase | template_id | Descripción |
|:----:|-------------|-------------|
| 0 | `ordenes_gt_signup` | Apuntarse a la batalla |
| 1 | `ordenes_gt_defensas` | Instrucciones de defensa por zona |
| 2 | `ordenes_gt_ataque` | Instrucciones de ataque |
| 3 | `ordenes_gt_cierre` | Cierre y resultados |

El cálculo de fase para GT es: `phase = days_since_start` (0-indexed, máximo 3).
Para BT es: `phase = days_since_start + 1` (1-indexed, máximo 6).

Este PR sigue el **mismo patrón exacto** que ya existe para BT, sin refactorizar.
Se agregarán los archivos, funciones y comandos necesarios paralelos a los de BT.

## Archivos a modificar

### 1. `modules/database.py`

Añadir tabla `gt_config` y funciones de acceso.

**Sqlite init** — En `init_database()` (o en `schema.sql`), añadir:
```sql
CREATE TABLE IF NOT EXISTS gt_config (
    id INTEGER PRIMARY KEY,
    start_date TEXT,
    updated_at TEXT
);
```

**Funciones nuevas** (mismo patrón que `get_bt_start_date` / `set_bt_start_date`):

```python
def get_gt_start_date() -> Optional[str]:
    """Obtiene la fecha de inicio de GT desde la DB."""

def set_gt_start_date(start_date: str) -> bool:
    """Establece la fecha de inicio de GT en la DB."""
```

### 2. `modules/scheduler.py`

Añadir templates de GT y nueva función de publicación.

**Constantes nuevas:**

```python
GT_TEMPLATES = {
    0: "ordenes_gt_signup",
    1: "ordenes_gt_defensas",
    2: "ordenes_gt_ataque",
    3: "ordenes_gt_cierre",
}

GT_START_DATE = date(2026, 7, 24)  # hardcoded fallback
```

**Funciones nuevas:**

```python
def get_gt_start() -> date:
    """Obtiene la fecha de inicio de GT desde DB o hardcoded."""
    # Mismo patrón que get_bt_start()

def get_template_order_gt(phase: int) -> str | None:
    """Obtiene la orden de GT de MongoDB por template_id."""
    # Mismo patrón que get_template_order() pero con GT_TEMPLATES

async def send_daily_gt_reminder(bot: Bot) -> None:
    """Envía el recordatorio diario de GT basado en la fecha."""
    # Igual que send_daily_reminder() pero:
    # - Usa get_gt_start()
    # - phase = days_since_start + 0 (0-indexed)
    # - max phase = 3
    # - GT_TEMPLATES
    # - Envía a los mismos aviso_chats y Discord webhooks

def send_daily_gt_reminder_sync(bot: Bot) -> None:
    """Versión síncrona para BackgroundScheduler."""
    import asyncio
    asyncio.run(send_daily_gt_reminder(bot))
```

**Registrar en scheduler** — En `create_scheduler()`, añadir segundo job:
```python
scheduler.add_job(
    send_daily_gt_reminder_sync,
    CronTrigger(hour=17, minute=0, second=0, timezone="UTC"),
    args=[bot],
    id="daily_gt_reminder",
    name="Daily 17:00 UTC GT reminder",
    replace_existing=True,
)
```

Añadir import de las nuevas funciones de database:
```python
from modules.database import (
    ...,
    get_gt_start_date,
    set_gt_start_date,
)
```

### 3. `bot.py`

Añadir comandos de GT.

**Nuevo import:**
```python
from modules.scheduler import (
    send_daily_gt_reminder,
    send_daily_gt_reminder_sync,
    get_template_order_gt,
    get_gt_start,
    GT_TEMPLATES,
)
```

**Nuevo handler:**
```python
@admin_only
async def set_gt_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /set_gt_date o /iniciar_gt - Establece la fecha de inicio de la próxima GT."""
    # Misma lógica que set_bt_date pero:
    # - No valida que sea lunes (la GT puede empezar cualquier día)
    # - Usa set_gt_start_date()

@admin_only
async def gt_random_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /orden_gt o /mensaje_gt - Envía la orden de GT de la fase actual."""
    # Similar a random_message pero:
    # - Calcula la fase actual con get_gt_start()
    # - Usa get_template_order_gt()
    # - Muestra "Fase X de GT" en el mensaje
```

**Registrar handlers:**
```python
app.add_handler(CommandHandler(["set_gt_date", "iniciar_gt"], set_gt_date))
app.add_handler(CommandHandler(["orden_gt", "mensaje_gt"], gt_random_message))
```

### 4. `.env` / `.env.example`

No requiere cambios — GT usa los mismos chats de avisos y webhooks que BT.

### 5. Documentación

Agregar los nuevos comandos al `README.md` en la tabla de comandos.

## Pruebas

1. Ejecutar `db.execute("CREATE TABLE IF NOT EXISTS gt_config ...")` para crear la tabla
2. Validar que `/set_gt_date 2026-07-24` persiste y se recupera correctamente
3. Validar que el scheduler ejecuta `send_daily_gt_reminder` a las 17:00 UTC
4. Validar que `/orden_gt` muestra la fase correcta
5. Verificar que no se rompe la funcionalidad existente de BT

## Notas

- La GT comparte los mismos `aviso_chats` que BT (no se necesita un tipo de chat separado).
- Si en el futuro se quiere un canal separado para GT, se puede añadir una variable de entorno
  `GT_AVISOS_CHAT_IDS` y filtrar por `chat_type="avisos_gt"`.
- Este PR es el paso 1. El PR 2 refactorizará DRY si se considera necesario.
