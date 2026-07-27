# PR 2: Refactorizar BT y GT con patrón BATTLE_TYPES

## Contexto

Después de implementar GT en el PR 1 siguiendo el mismo patrón que BT,
el código tiene mucha duplicación:

- `get_bt_start()` / `get_gt_start()` → casi idénticas
- `get_template_order()` / `get_template_order_gt()` → solo cambia el dict
- `send_daily_reminder()` / `send_daily_gt_reminder()` → mismas diferencias
- `set_bt_date()` / `set_gt_date()` → diferencia en validación de día

Este PR refactoriza usando un diccionario `BATTLE_TYPES` que centraliza
toda la configuración, siguiendo el mismo enfoque implementado en el
Discord bot `probe-droid-swgoh-bot` (rama `feat/guild-orders-bt`).

## Diseño

### BATTLE_TYPES

```python
BATTLE_TYPES = {
    "bt": {
        "name": "Batalla Territorial",
        "name_short": "BT",
        "templates": {
            1: "ordenes_fase_1",
            2: "ordenes_fase_2",
            3: "ordenes_fase_3",
            4: "ordenes_fase_4",
            5: "ordenes_fase_5_mandalore",
            6: "ordenes_fase_6_mandalore",
        },
        "phase_offset": 1,  # phase = days_since + 1
        "max_phase": 6,
        "post_hour": 17,
        "post_minute": 0,
        "monday_only": True,  # warning si no es lunes
    },
    "gt": {
        "name": "Guerra Territorial",
        "name_short": "GT",
        "templates": {
            0: "ordenes_gt_signup",
            1: "ordenes_gt_defensas",
            2: "ordenes_gt_ataque",
            3: "ordenes_gt_cierre",
        },
        "phase_offset": 0,  # phase = days_since + 0
        "max_phase": 3,
        "post_hour": 19,
        "post_minute": 0,
        "monday_only": False,
    },
}
```

## Archivos a modificar

### 1. `modules/database.py`

**Reemplazar** `bt_config` y `gt_config` por una tabla genérica:

```sql
CREATE TABLE IF NOT EXISTS event_dates (
    event_type TEXT PRIMARY KEY,
    start_date TEXT,
    updated_at TEXT
);
```

**Migración:** Si existen datos en `bt_config` o `gt_config`, migrarlos a `event_dates`.
Usar el mismo patrón de migración que en `probe-droid-swgoh-bot/bot.py`:

```python
# En init_database() o en init_db()
for table, event_type in [("bt_config", "bt"), ("gt_config", "gt")]:
    row = conn.execute(f"SELECT start_date FROM {table} WHERE id = 1").fetchone()
    if row:
        existing = conn.execute("SELECT 1 FROM event_dates WHERE event_type = ?", (event_type,)).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO event_dates (event_type, start_date, updated_at) VALUES (?, ?, datetime('now'))",
                (event_type, row[0]),
            )
```

**Funciones genéricas:**
```python
def get_event_date(event_type: str) -> Optional[str]:
def set_event_date(event_type: str, start_date: str) -> bool:
```

**Mantener wrappers para compatibilidad:**
```python
def get_bt_start_date() -> Optional[str]:
    return get_event_date("bt")

def set_bt_start_date(start_date: str) -> bool:
    return set_event_date("bt", start_date)

def get_gt_start_date() -> Optional[str]:
    return get_event_date("gt")

def set_gt_start_date(start_date: str) -> bool:
    return set_event_date("gt", start_date)
```

### 2. `modules/scheduler.py`

**Agregar BATTLE_TYPES** en lugar de las constantes sueltas:

```python
BATTLE_TYPES = {...}  # dict de arriba
```

**Reemplazar funciones duplicadas por funciones genéricas:**

```python
def get_start(event_type: str) -> date:
    """Obtiene la fecha de inicio desde DB o hardcoded."""
    cfg = BATTLE_TYPES[event_type]
    ...

def get_phase(event_type: str) -> int | None:
    """Calcula la fase actual para un tipo de evento."""
    start = get_start(event_type)
    today = datetime.now(ZoneInfo("UTC")).date()
    days_since = (today - start).days
    if days_since < 0:
        return None
    cfg = BATTLE_TYPES[event_type]
    phase = days_since + cfg["phase_offset"]
    if phase > cfg["max_phase"]:
        return None
    return phase

def get_template_order_by_type(event_type: str, phase: int) -> str | None:
    """Obtiene la orden de MongoDB por tipo de evento y fase."""
    cfg = BATTLE_TYPES[event_type]
    template_id = cfg["templates"].get(phase)
    ...

async def send_daily_reminder_by_type(bot: Bot, event_type: str) -> None:
    """Envía el recordatorio diario para un tipo de evento."""
    cfg = BATTLE_TYPES[event_type]
    phase = get_phase(event_type)
    ...
```

**Simplificar send_daily_reminder como wrapper:**
```python
async def send_daily_reminder(bot: Bot) -> None:
    await send_daily_reminder_by_type(bot, "bt")

async def send_daily_gt_reminder(bot: Bot) -> None:
    await send_daily_reminder_by_type(bot, "gt")
```

**Versiones síncronas igual que antes.**

**En create_scheduler()** — no cambia, ya registra ambos jobs.

### 3. `bot.py`

**Reemplazar comandos duplicados por función compartida:**

```python
async def _set_date_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, event_type: str) -> None:
    cfg = BATTLE_TYPES[event_type]
    # Lógica común de set_date:
    # - Validar formato
    # - Validar día (si monday_only)
    # - Guardar con set_event_date()
    # - Responder

async def _orden_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, event_type: str) -> None:
    cfg = BATTLE_TYPES[event_type]
    # Lógica común de orden:
    # - Obtener fase actual o específica
    # - Obtener orden de MongoDB
    # - Formatear y enviar
```

**Simplificar handlers:**
```python
@admin_only
async def set_bt_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _set_date_cmd(update, context, "bt")

@admin_only
async def set_gt_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _set_date_cmd(update, context, "gt")
```

**Ayuda** — Opcionalmente añadir un comando `/ayuda` o actualizar `/help`
para mostrar todos los comandos dinámicamente desde BATTLE_TYPES.

### 4. `modules/helpers.py`

No requiere cambios significativos, pero `get_help_text()` podría actualizarse
para incluir GT si se modifica el texto de ayuda en i18n.

## Pruebas

1. Migración de datos existentes: verificar que `event_dates` tenga los datos
   de `bt_config` y `gt_config` después de la migración
2. Verificar que `get_bt_start_date()` y `get_gt_start_date()` sigan funcionando
   a través de los wrappers
3. Verificar que la publicación automática de BT y GT funciona igual que antes
4. Verificar que `/set_bt_date` y `/set_gt_date` funcionan
5. Verificar que no se pierde la funcionalidad de BT existente

## Referencia

El código de referencia implementado está en `probe-droid-swgoh-bot/bot.py`
(rama `feat/guild-orders-bt`, commit `c15051a`), específicamente las secciones:
- `BATTLE_TYPES` — constante de configuración
- `get_event_date()` / `set_event_date()` — SQLite genérico
- `get_phase()` — cálculo genérico de fase
- `get_template_order(templates, phase)` — MongoDB genérico
- `publish_order(event_type)` — publicación genérica
- `_set_date_cmd()` / `_orden_cmd()` — comandos compartidos

## Notas

- Este PR es puramente refactor. No añade funcionalidad nueva.
- La tabla `event_dates` convive con `bt_config` y `gt_config` viejas,
  permitiendo rollback si es necesario.
- Los wrappers `get_bt_start_date()` / `set_bt_start_date()` se mantienen
  para no romper importaciones externas.
