"""
Bot de Discord para detectar códigos regalo y promociones de Star Wars: Galaxy of Heroes.

Monitoriza fuentes RSS para códigos promo y publica órdenes de Batalla Territorial (BT)
y Guerra Territorial (GT) desde MongoDB en canales de Discord configurables.

Versión: 5.0
"""

import discord
import feedparser
import logging
import sqlite3
import os
from datetime import datetime, timezone, date, timedelta
from discord.ext import tasks, commands
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo

load_dotenv()

# ─────────────────────────────────────────────
# CONFIGURACIÓN GENERAL
# ─────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
GENERAL_CHANNEL_ID = int(os.getenv("GENERAL_CHANNEL_ID", "0"))
CODE_ALERTS_CHANNEL_ID = int(os.getenv("CODE_ALERTS_CHANNEL_ID", str(GENERAL_CHANNEL_ID)))
BT_GUILD_ORDERS_CHANNEL_ID = int(os.getenv("BT_GUILD_ORDERS_CHANNEL_ID", str(GENERAL_CHANNEL_ID)))
GT_GUILD_ORDERS_CHANNEL_ID = int(os.getenv("GT_GUILD_ORDERS_CHANNEL_ID", str(GENERAL_CHANNEL_ID)))
CHECK_EVERY = 15
POST_TIMEZONE = "UTC"

# IDs de usuarios autorizados a usar comandos admin via DM (separados por coma)
_ADMIN_USER_IDS_ENV = os.getenv("ADMIN_USER_IDS", "")
ADMIN_USER_IDS = {int(uid.strip()) for uid in _ADMIN_USER_IDS_ENV.split(",") if uid.strip()}

MONTHS_ES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
WEEKDAYS_ES = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]

# ─────────────────────────────────────────────
# CONFIGURACIÓN POR TIPO DE EVENTO
# ─────────────────────────────────────────────
BATTLE_TYPES = {
    "bt": {
        "name": "Batalla Territorial",
        "name_short": "BT",
        "channel": BT_GUILD_ORDERS_CHANNEL_ID,
        "templates": {
            1: "ordenes_fase_1",
            2: "ordenes_fase_2",
            3: "ordenes_fase_3",
            4: "ordenes_fase_4",
            5: "ordenes_fase_5_mandalore",
            6: "ordenes_fase_6_mandalore",
        },
        "phase_offset": 1,
        "max_phase": 6,
        "post_hour": 17,
        "post_minute": 0,
    },
    "gt": {
        "name": "Guerra Territorial",
        "name_short": "GT",
        "channel": GT_GUILD_ORDERS_CHANNEL_ID,
        "templates": {
            0: "ordenes_gt_signup",
            1: "ordenes_gt_defensas",
            2: "ordenes_gt_ataque",
            3: "ordenes_gt_cierre",
        },
        "phase_offset": 0,
        "max_phase": 3,
        "post_hour": 17,
        "post_minute": 0,
    },
}

SOURCES = [
    {
        "name": "Reddit SWGoH (Filtrado)",
        "url": "https://www.reddit.com/r/SWGalaxyOfHeroes/search.rss?q=title%3A%22code%22+OR+title%3A%22promo%22+OR+title%3A%22gift%22&restrict_sr=on&sort=new&t=all",
        "keywords": ["promo code", "gift code", "redeem", "free gift", "active code"],
        "color": discord.Color.gold()
    },
    {
        "name": "Anuncios Oficiales (Foros EA)",
        "url": "https://forums.galaxy-of-heroes.starwars.ea.com/categories/news-and-announcements/feed.rss",
        "keywords": ["compensation", "gift", "make-good", "webstore", "free"],
        "color": discord.Color.blue()
    }
]

BLACKLIST = [
    "ally code", "allycode", "friend code", "my code", "add me", "roster",
    "how", "help", "issue", "error", "missing", "question", "?", "why",
    "starkiller", "lsb", "bundle", "purchase", "support", "banned", "cheat"
]

# ─────────────────────────────────────────────
# LOGS Y DB
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DB_PATH = "bot_data.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS seen_posts (post_id TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS bt_config (id INTEGER PRIMARY KEY, start_date TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS event_dates (event_type TEXT PRIMARY KEY, start_date TEXT, updated_at TEXT)")

    # Migrar datos viejos de bt_config a event_dates si existen
    row = conn.execute("SELECT start_date FROM bt_config WHERE id = 1").fetchone()
    if row:
        existing = conn.execute("SELECT 1 FROM event_dates WHERE event_type = 'bt'").fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO event_dates (event_type, start_date, updated_at) VALUES ('bt', ?, datetime('now'))",
                (row[0],),
            )
            log.info("BT start date migrada a event_dates: %s", row[0])

    conn.commit()
    conn.close()


def is_new_post(post_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM seen_posts WHERE post_id = ?", (post_id,))
    result = c.fetchone()
    if not result:
        c.execute("INSERT INTO seen_posts (post_id) VALUES (?)", (post_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


def get_event_date(event_type: str) -> str | None:
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT start_date FROM event_dates WHERE event_type = ?", (event_type,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        log.error("Error leyendo fecha %s: %s", event_type, e)
        return None


def set_event_date(event_type: str, start_date: str) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO event_dates (event_type, start_date, updated_at) VALUES (?, ?, datetime('now'))",
            (event_type, start_date),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Error guardando fecha %s: %s", event_type, e)
        return False


def get_bt_start_date() -> str | None:
    return get_event_date("bt")


def set_bt_start_date(start_date: str) -> bool:
    return set_event_date("bt", start_date)


# ─────────────────────────────────────────────
# MONGODB
# ─────────────────────────────────────────────
_mongo_client = None


def get_mongo_client():
    global _mongo_client
    if _mongo_client is None:
        from pymongo import MongoClient
        uri = os.getenv("MONGODB_URI", "")
        if not uri:
            raise ValueError("MONGODB_URI no configurado en .env")
        _mongo_client = MongoClient(uri, maxPoolSize=5, serverSelectionTimeoutMS=5000)
        log.info("MongoDB conectado")
    return _mongo_client


def get_mongo_db():
    db_name = os.getenv("MONGODB_DB_NAME", "orders_manager")
    return get_mongo_client()[db_name]


def get_template_order(templates: dict, phase: int) -> str | None:
    try:
        db = get_mongo_db()
        template_id = templates.get(phase)
        if not template_id:
            return None
        results = list(db["orders"].find({"is_active": True, "template_id": template_id}))
        if results:
            return results[0].get("content")
        log.warning("No hay orden para template_id %s", template_id)
        return None
    except Exception as e:
        log.error("Error obteniendo orden de MongoDB: %s", e)
        return None


def get_random_order() -> str | None:
    try:
        db = get_mongo_db()
        pipeline = [{"$match": {"is_active": True}}, {"$sample": {"size": 1}}]
        results = list(db["orders"].aggregate(pipeline))
        if results:
            return results[0].get("content")
        return None
    except Exception as e:
        log.error("Error obteniendo orden aleatoria de MongoDB: %s", e)
        return None


# ─────────────────────────────────────────────
# LÓGICA COMPARTIDA: BT / GT
# ─────────────────────────────────────────────
def get_phase(event_type: str) -> int | None:
    cfg = BATTLE_TYPES.get(event_type)
    if not cfg:
        return None
    start_str = get_event_date(event_type)
    if not start_str:
        return None
    try:
        start = date.fromisoformat(start_str)
        today = datetime.now(timezone.utc).date()
        days_since = (today - start).days
        if days_since < 0:
            return None
        phase = days_since + cfg["phase_offset"]
        if phase > cfg["max_phase"]:
            return None
        return phase
    except Exception as e:
        log.error("Error calculando fase %s: %s", event_type, e)
        return None


def format_date_es(d: date) -> str:
    return f"{d.day} de {MONTHS_ES[d.month].capitalize()}"


def format_weekday_date_es(d: date) -> str:
    weekday = WEEKDAYS_ES[d.weekday()]
    return f"{weekday} {format_date_es(d)}:"


# ─────────────────────────────────────────────
# LÓGICA DE FILTRADO RSS
# ─────────────────────────────────────────────
def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = " ".join(soup.get_text().split())
    return text[:300] + "..." if len(text) > 300 else text


def is_authorized(ctx) -> bool:
    if not ctx.guild:
        return ctx.author.id in ADMIN_USER_IDS
    perms = ctx.author.guild_permissions
    if perms.administrator or perms.manage_guild or perms.ban_members or perms.kick_members:
        return True
    return False


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ─────────────────────────────────────────────
# PUBLICACIÓN DE ÓRDENES (COMPARTIDO)
# ─────────────────────────────────────────────
PUBLISH_COLORS = {
    "bt": discord.Color.dark_purple(),
    "gt": discord.Color.dark_teal(),
}

PUBLISH_FOOTERS = {
    "bt": "Sonda Droid • Órdenes de Batalla Territorial",
    "gt": "Sonda Droid • Órdenes de Guerra Territorial",
}


async def publish_order(event_type: str):
    cfg = BATTLE_TYPES.get(event_type)
    if not cfg:
        return

    channel = bot.get_channel(cfg["channel"])
    if not channel:
        log.warning("Canal %s no encontrado", event_type)
        return

    phase = get_phase(event_type)
    if phase is None:
        start = get_event_date(event_type)
        if start:
            log.info("%s fuera de rango o no iniciada (start=%s)", event_type, start)
        else:
            log.info("%s no configurada", event_type)
        return

    order = get_template_order(cfg["templates"], phase)
    if not order:
        log.warning("No hay orden para %s fase %s", event_type, phase)
        return

    start_str = get_event_date(event_type)
    if start_str:
        start = date.fromisoformat(start_str)
        current_date = start + timedelta(days=phase - cfg["phase_offset"])
        full_message = f"{format_weekday_date_es(current_date)}\n\n{order}"
    else:
        full_message = f"**Fase {phase}**\n\n{order}"

    embed = discord.Embed(
        title=f"{cfg['name']} — Fase {phase}",
        description=full_message,
        color=PUBLISH_COLORS.get(event_type, discord.Color.default()),
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=PUBLISH_FOOTERS.get(event_type, "Sonda Droid"))

    await channel.send(embed=embed)
    log.info("%s fase %s publicada en canal %s", event_type, phase, cfg["channel"])


# ─────────────────────────────────────────────
# TAREAS PROGRAMADAS
# ─────────────────────────────────────────────
@tasks.loop(time=datetime.strptime("17:00:00", "%H:%M:%S").time())
async def daily_bt_order():
    await publish_order("bt")


@tasks.loop(time=datetime.strptime("17:00:00", "%H:%M:%S").time())
async def daily_gt_order():
    await publish_order("gt")


@tasks.loop(minutes=CHECK_EVERY)
async def scan_feeds():
    channel = bot.get_channel(CODE_ALERTS_CHANNEL_ID)
    if not channel:
        return

    for source in SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries:
                entry_id = getattr(entry, "id", entry.link)
                if not is_new_post(entry_id):
                    continue

                title_lower = entry.title.lower()

                if title_lower.strip().endswith("?") or "ally" in title_lower:
                    continue

                if any(b in title_lower for b in BLACKLIST):
                    continue

                is_valid = any(k in title_lower for k in source["keywords"])
                if not is_valid:
                    continue

                summary = clean_html(getattr(entry, "summary", ""))

                embed = discord.Embed(
                    title=entry.title[:250],
                    url=entry.link,
                    color=source["color"],
                    description=f"**Fuente:** {source['name']}\n\n{summary}",
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(text="Sonda Droid • Modo Estricto ACTIVO 🛡️")

                await channel.send(
                    content="🚨 **ALERTA: Posible Recompensa o Código Detectado** 🚨",
                    embed=embed
                )
                log.info("Aceptado: %s", entry.title)

        except Exception as e:
            log.error("Error: %s", e)


# ─────────────────────────────────────────────
# EVENTO: ON_READY
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    log.info("Sonda v5 activa como %s", bot.user)
    init_db()
    if not scan_feeds.is_running():
        scan_feeds.start()
    if not daily_bt_order.is_running():
        daily_bt_order.start()
    if not daily_gt_order.is_running():
        daily_gt_order.start()
    bt_time = f"{BATTLE_TYPES['bt']['post_hour']:02d}:{BATTLE_TYPES['bt']['post_minute']:02d} UTC"
    gt_time = f"{BATTLE_TYPES['gt']['post_hour']:02d}:{BATTLE_TYPES['gt']['post_minute']:02d} UTC"
    log.info("RSS scan: cada %s min | BT daily: %s | GT daily: %s", CHECK_EVERY, bt_time, gt_time)


# ─────────────────────────────────────────────
# COMANDOS
# ─────────────────────────────────────────────
@bot.command()
async def estado(ctx):
    embed = discord.Embed(
        title="Sonda Droid SWGoH",
        description="Bot operativo con filtros anti-AllyCode, órdenes BT y GT.",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="RSS Codes", value=f"Cada {CHECK_EVERY} min en <#{CODE_ALERTS_CHANNEL_ID}>", inline=False)

    today = datetime.now(timezone.utc).date()
    for key in ("bt", "gt"):
        cfg = BATTLE_TYPES[key]
        start = get_event_date(key)
        phase = get_phase(key)
        if start:
            info = f"Inicio: {start}"
            if phase is not None:
                info += f" | Fase actual: {phase}"
            elif date.fromisoformat(start) > today:
                info += " | Por iniciar"
            else:
                info += " | Finalizada"
        else:
            info = "No configurada"
        post_time = f"{cfg['post_hour']:02d}:{cfg['post_minute']:02d} UTC"
        embed.add_field(
            name=f"{cfg['name']} ({cfg['name_short']})",
            value=f"Diario {post_time} en <#{cfg['channel']}>\n{info}",
            inline=False,
        )

    await ctx.send(embed=embed)


async def _set_date_cmd(ctx, event_type: str, fecha: str | None):
    cfg = BATTLE_TYPES.get(event_type)
    if not cfg:
        return

    if not is_authorized(ctx):
        await ctx.send("🚫 No tienes permisos para usar este comando.")
        return

    cmd_name = f"!set_{event_type}_date"

    if not fecha:
        current = get_event_date(event_type)
        msg = f"⚠️ Uso: `{cmd_name} YYYY-MM-DD`\n\n"
        msg += f"Fecha actual: {current or 'No configurada'}\n\n"
        msg += f"Ejemplo:\n`{cmd_name} 2026-07-06`"
        await ctx.send(msg)
        return

    try:
        parsed = date.fromisoformat(fecha)
    except ValueError:
        await ctx.send(f"⚠️ Formato inválido. Usa YYYY-MM-DD\nEjemplo: `{cmd_name} 2026-07-06`")
        return

    if event_type == "bt" and parsed.weekday() != 0:
        next_monday = parsed + timedelta(days=(7 - parsed.weekday()) % 7)
        await ctx.send(
            f"⚠️ Advertencia: {fecha} no es lunes.\n"
            f"Próximo lunes: {next_monday.isoformat()}\n"
            "Continuando con la fecha indicada..."
        )

    if set_event_date(event_type, fecha):
        await ctx.send(f"✅ Fecha de {cfg['name']} configurada: {fecha}")
        log.info("%s start date set to %s by admin %s", event_type, fecha, ctx.author.id)
    else:
        await ctx.send("❌ Error guardando la fecha")


@bot.command()
async def set_bt_date(ctx, *, fecha: str = None):
    await _set_date_cmd(ctx, "bt", fecha)


@bot.command()
async def set_gt_date(ctx, *, fecha: str = None):
    await _set_date_cmd(ctx, "gt", fecha)


async def _orden_cmd(ctx, event_type: str, fase: str | None):
    cfg = BATTLE_TYPES.get(event_type)
    if not cfg:
        return

    if not is_authorized(ctx):
        await ctx.send("🚫 No tienes permisos para usar este comando.")
        return

    cmd_name = f"!orden_{event_type}"

    if fase:
        try:
            phase = int(fase)
            if phase < cfg["phase_offset"] or phase > cfg["max_phase"]:
                await ctx.send(f"⚠️ La fase debe estar entre {cfg['phase_offset']} y {cfg['max_phase']}.")
                return
        except ValueError:
            await ctx.send(f"⚠️ Uso: `{cmd_name} <{cfg['phase_offset']}-{cfg['max_phase']}>` para una fase específica, o `{cmd_name}` para la fase actual.")
            return
    else:
        phase = get_phase(event_type)
        if phase is None:
            await ctx.send(f"⚠️ No hay {cfg['name_short']} activa. Configura la fecha con `!set_{event_type}_date YYYY-MM-DD`")
            return

    order = get_template_order(cfg["templates"], phase)
    if not order:
        await ctx.send(f"⚠️ No se encontró orden para la fase {phase} en MongoDB.")
        return

    start_str = get_event_date(event_type)
    if start_str:
        start = date.fromisoformat(start_str)
        current_date = start + timedelta(days=phase - cfg["phase_offset"])
        full_message = f"{format_weekday_date_es(current_date)}\n\n{order}"
    else:
        full_message = f"**Fase {phase}**\n\n{order}"

    embed = discord.Embed(
        title=f"{cfg['name']} — Fase {phase}",
        description=full_message,
        color=PUBLISH_COLORS.get(event_type, discord.Color.default()),
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=PUBLISH_FOOTERS.get(event_type, "Sonda Droid"))

    await ctx.send(embed=embed)
    log.info("%s fase %s publicada por admin %s", event_type, phase, ctx.author.id)


@bot.command()
async def orden_bt(ctx, fase: str = None):
    await _orden_cmd(ctx, "bt", fase)


@bot.command()
async def orden_gt(ctx, fase: str = None):
    await _orden_cmd(ctx, "gt", fase)


@bot.command()
async def ayuda(ctx):
    if not is_authorized(ctx):
        await ctx.send("🚫 No tienes permisos para usar este comando.")
        return

    embed = discord.Embed(
        title="Sonda Droid — Comandos disponibles",
        description="Bot de códigos RSS y órdenes de gremio para SWGoH.",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc),
    )

    embed.add_field(
        name="📡 Generales",
        value="`!estado` — Estado del bot, BT y GT\n`!ayuda` — Esta ayuda\nLos comandos admin también funcionan por MD si tu ID está en `ADMIN_USER_IDS`.",
        inline=False,
    )

    embed.add_field(
        name="🎁 Códigos RSS",
        value=f"Publicación automática cada {CHECK_EVERY} min en <#{CODE_ALERTS_CHANNEL_ID}>",
        inline=False,
    )

    for key in ("bt", "gt"):
        cfg = BATTLE_TYPES[key]
        start_phase = cfg["phase_offset"]
        end_phase = cfg["max_phase"]
        post_time = f"{cfg['post_hour']:02d}:{cfg['post_minute']:02d} UTC"
        embed.add_field(
            name=f"⚔️ {cfg['name']} ({cfg['name_short']})",
            value=(
                f"`!set_{key}_date YYYY-MM-DD` — Configurar fecha de inicio\n"
                f"`!orden_{key} <{start_phase}-{end_phase}>` — Publicar fase específica\n"
                f"`!orden_{key}` — Publicar fase actual\n"
                f"Publicación automática: {post_time} en <#{cfg['channel']}>"
            ),
            inline=False,
        )

    await ctx.send(embed=embed)


if __name__ == "__main__":
    bot.run(BOT_TOKEN)
