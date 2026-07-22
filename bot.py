"""
Bot de Discord para detectar códigos regalo y promociones de Star Wars: Galaxy of Heroes.

Este bot monitoriza fuentes RSS de Reddit y foros oficiales de EA para detectar
automáticamente códigos promo, códigos regalo y compensaciones. Utiliza un sistema
de filtros multicapa para evitar spam (ally codes, preguntas, etc.).

Además, publica órdenes de Batalla Territorial (BT) desde MongoDB en un canal de Discord
configurable, con un comando !set_bt_date para administradores y publicación automática diaria.

Versión: 4.0
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
# CONFIGURACIÓN
# ─────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
GUILD_ORDERS_CHANNEL_ID = int(os.getenv("GUILD_ORDERS_CHANNEL_ID", str(CHANNEL_ID)))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
CHECK_EVERY = 15
BT_POST_HOUR = 17
BT_POST_MINUTE = 0
BT_POST_TIMEZONE = "UTC"

MONTHS_ES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
WEEKDAYS_ES = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]

BT_TEMPLATES = {
    1: "ordenes_fase_1",
    2: "ordenes_fase_2",
    3: "ordenes_fase_3",
    4: "ordenes_fase_4",
    5: "ordenes_fase_5_mandalore",
    6: "ordenes_fase_6_mandalore",
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


def init_db():
    conn = sqlite3.connect("bot_data.db")
    conn.execute("CREATE TABLE IF NOT EXISTS seen_posts (post_id TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS bt_config (id INTEGER PRIMARY KEY, start_date TEXT, updated_at TEXT)")
    conn.commit()
    conn.close()


def is_new_post(post_id: str) -> bool:
    conn = sqlite3.connect("bot_data.db")
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


def get_bt_start_date() -> str | None:
    try:
        conn = sqlite3.connect("bot_data.db")
        c = conn.cursor()
        c.execute("SELECT start_date FROM bt_config WHERE id = 1")
        row = c.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        log.error("Error leyendo bt_start_date: %s", e)
        return None


def set_bt_start_date(start_date: str) -> bool:
    try:
        conn = sqlite3.connect("bot_data.db")
        conn.execute(
            "INSERT OR REPLACE INTO bt_config (id, start_date, updated_at) VALUES (1, ?, datetime('now'))",
            (start_date,),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error("Error guardando bt_start_date: %s", e)
        return False


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


def get_template_order(phase: int) -> str | None:
    try:
        db = get_mongo_db()
        template_id = BT_TEMPLATES.get(phase)
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


def get_bt_phase() -> int | None:
    bt_start_str = get_bt_start_date()
    if not bt_start_str:
        return None
    try:
        bt_start = date.fromisoformat(bt_start_str)
        today = datetime.now(timezone.utc).date()
        days_since = (today - bt_start).days
        if days_since < 0:
            return None
        phase = days_since + 1
        if phase > 6:
            return None
        return phase
    except Exception as e:
        log.error("Error calculando fase BT: %s", e)
        return None


def format_date_es(d: date) -> str:
    return f"{d.day} de {MONTHS_ES[d.month].capitalize()}"


def format_weekday_date_es(d: date) -> str:
    weekday = WEEKDAYS_ES[d.weekday()]
    return f"{weekday} {format_date_es(d)}:"


# ─────────────────────────────────────────────
# LÓGICA DE FILTRADO
# ─────────────────────────────────────────────
def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = " ".join(soup.get_text().split())
    return text[:300] + "..." if len(text) > 300 else text


def is_authorized(ctx) -> bool:
    if ctx.author.id in ADMIN_IDS:
        return True
    if not ctx.guild:
        return False
    perms = ctx.author.guild_permissions
    if perms.administrator or perms.manage_guild or perms.ban_members or perms.kick_members:
        return True
    return False


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ─────────────────────────────────────────────
# TAREA DIARIA: ÓRDENES BT
# ─────────────────────────────────────────────
@tasks.loop(time=datetime.strptime(f"{BT_POST_HOUR:02d}:{BT_POST_MINUTE:02d}:00", "%H:%M:%S").time())
async def daily_bt_order():
    now = datetime.now(ZoneInfo(BT_POST_TIMEZONE))
    log.info("Ejecutando daily_bt_order a las %s", now.strftime("%H:%M UTC"))

    channel = bot.get_channel(GUILD_ORDERS_CHANNEL_ID)
    if not channel:
        log.warning("Canal de órdenes BT no encontrado (GUILD_ORDERS_CHANNEL_ID=%s)", GUILD_ORDERS_CHANNEL_ID)
        return

    phase = get_bt_phase()
    if phase is None:
        bt_start = get_bt_start_date()
        if bt_start:
            log.info("BT fuera de rango o no iniciada aún (start=%s)", bt_start)
        else:
            log.info("BT no configurada - no se publica orden")
        return

    order = get_template_order(phase)
    if not order:
        log.warning("No se encontró orden para fase %s en MongoDB", phase)
        return

    bt_start = date.fromisoformat(get_bt_start_date())
    current_date = bt_start + timedelta(days=phase - 1)
    full_message = f"{format_weekday_date_es(current_date)}\n\n{order}"

    embed = discord.Embed(
        title=f"Órdenes BT — Fase {phase}",
        description=full_message,
        color=discord.Color.dark_purple(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text="Sonda Droid • Órdenes de Batalla Territorial")

    await channel.send(embed=embed)
    log.info("Orden BT fase %s publicada en canal %s", phase, GUILD_ORDERS_CHANNEL_ID)


# ─────────────────────────────────────────────
# TAREA PERIÓDICA: ESCANEO RSS
# ─────────────────────────────────────────────
@tasks.loop(minutes=CHECK_EVERY)
async def scan_feeds():
    channel = bot.get_channel(CHANNEL_ID)
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
    log.info("Sonda v4 activa como %s", bot.user)
    init_db()
    if not scan_feeds.is_running():
        scan_feeds.start()
    if not daily_bt_order.is_running():
        daily_bt_order.start()
    log.info("RSS scan: cada %s min | BT daily: %s:%s %s",
             CHECK_EVERY, BT_POST_HOUR, BT_POST_MINUTE, BT_POST_TIMEZONE)


# ─────────────────────────────────────────────
# COMANDOS
# ─────────────────────────────────────────────
@bot.command()
async def estado(ctx):
    embed = discord.Embed(
        title="Sonda Droid SWGoH",
        description="Bot operativo con filtros anti-AllyCode y publicación de órdenes BT.",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="RSS Codes", value=f"Cada {CHECK_EVERY} min en <#{CHANNEL_ID}>", inline=False)
    embed.add_field(name="Órdenes BT", value=f"Diario {BT_POST_HOUR:02d}:{BT_POST_MINUTE:02d} UTC en <#{GUILD_ORDERS_CHANNEL_ID}>", inline=False)

    bt_start = get_bt_start_date()
    phase = get_bt_phase()
    if bt_start:
        bt_info = f"Inicio: {bt_start}"
        if phase:
            bt_info += f" | Fase actual: {phase}"
        else:
            bt_info += " | No activa"
    else:
        bt_info = "No configurada"
    embed.add_field(name="BT Config", value=bt_info, inline=False)

    await ctx.send(embed=embed)


@bot.command()
async def set_bt_date(ctx, *, fecha: str = None):
    if not is_authorized(ctx):
        await ctx.send("🚫 No tienes permisos para usar este comando.")
        return

    if not fecha:
        current = get_bt_start_date()
        msg = "⚠️ Uso: `!set_bt_date YYYY-MM-DD`\n\n"
        msg += f"Fecha actual: {current or 'No configurada'}\n\n"
        msg += "Ejemplo:\n`!set_bt_date 2026-07-06`"
        await ctx.send(msg)
        return

    try:
        bt_date = date.fromisoformat(fecha)
    except ValueError:
        await ctx.send("⚠️ Formato inválido. Usa YYYY-MM-DD\nEjemplo: `!set_bt_date 2026-07-06`")
        return

    today = datetime.now(timezone.utc).date()
    if bt_date < today:
        await ctx.send(f"⚠️ La fecha debe ser posterior a hoy.\nHoy: {today.isoformat()}")
        return

    if bt_date.weekday() != 0:
        next_monday = bt_date + timedelta(days=(7 - bt_date.weekday()) % 7)
        await ctx.send(
            f"⚠️ Advertencia: {fecha} no es lunes.\n"
            f"Próximo lunes: {next_monday.isoformat()}\n"
            "Continuando con la fecha indicada..."
        )

    if set_bt_start_date(fecha):
        await ctx.send(f"✅ Fecha de BT configurada: {fecha}")
        log.info("BT start date set to %s by admin %s", fecha, ctx.author.id)
    else:
        await ctx.send("❌ Error guardando la fecha")


@bot.command()
async def orden(ctx, fase: str = None):
    """Publica la orden de una fase específica o la fase actual si no se especifica."""
    if not is_authorized(ctx):
        await ctx.send("🚫 No tienes permisos para usar este comando.")
        return

    if fase:
        try:
            phase = int(fase)
            if phase < 1 or phase > 6:
                await ctx.send("⚠️ La fase debe estar entre 1 y 6.")
                return
        except ValueError:
            await ctx.send("⚠️ Uso: `!orden <1-6>` para una fase específica, o `!orden` para la fase actual.")
            return
    else:
        phase = get_bt_phase()
        if phase is None:
            await ctx.send("⚠️ No hay BT activa. Configura la fecha con `!set_bt_date YYYY-MM-DD`")
            return

    order = get_template_order(phase)
    if not order:
        await ctx.send(f"⚠️ No se encontró orden para la fase {phase} en MongoDB.")
        return

    bt_start_str = get_bt_start_date()
    if bt_start_str:
        bt_start = date.fromisoformat(bt_start_str)
        current_date = bt_start + timedelta(days=phase - 1)
        full_message = f"{format_weekday_date_es(current_date)}\n\n{order}"
    else:
        full_message = f"**Fase {phase}**\n\n{order}"

    embed = discord.Embed(
        title=f"Órdenes BT — Fase {phase}",
        description=full_message,
        color=discord.Color.dark_purple(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text="Sonda Droid • Órdenes de Batalla Territorial")

    await ctx.send(embed=embed)
    log.info("Orden BT fase %s publicada por admin %s", phase, ctx.author.id)


if __name__ == "__main__":
    bot.run(BOT_TOKEN)
