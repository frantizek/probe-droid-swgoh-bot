"""
Bot de Discord para detectar códigos regalo y promociones de Star Wars: Galaxy of Heroes.

Este bot monitoriza fuentes RSS de Reddit y foros oficiales de EA para detectar
automáticamente códigos promo, códigos regalo y compensaciones. Utiliza un sistema
de filtros multicapa para evitar spam (ally codes, preguntas, etc.).

Versión: 3.0
"""

import discord
import feedparser
import logging
import sqlite3
import re
import os
from datetime import datetime, timezone
from discord.ext import tasks, commands
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

# ─────────────────────────────────────────────
# CONFIGURACIÓN QUIRÚRGICA
# ─────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
CHECK_EVERY = 15

SOURCES = [
    {
        "name": "Reddit SWGoH (Filtrado)",
        "url": "https://www.reddit.com/r/SWGalaxyOfHeroes/search.rss?q=title%3A%22code%22+OR+title%3A%22promo%22+OR+title%3A%22gift%22&restrict_sr=on&sort=new&t=all",
        # Quitamos "code" a secas de las keywords de Reddit para evitar Ally Codes
        "keywords": ["promo code", "gift code", "redeem", "free gift", "active code"],
        "color": discord.Color.gold()
    },
    {
        "name": "Anuncios Oficiales (Foros EA)",
        "url": "https://forums.galaxy-of-heroes.starwars.ea.com/categories/news-and-announcements/feed.rss",
        # En el foro oficial sí confiamos en estas palabras porque solo postean DEVS
        "keywords": ["compensation", "gift", "make-good", "webstore", "free"],
        "color": discord.Color.blue()
    }
]

# Blacklist reforzada: 'ally' es la clave para eliminar el spam
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
    """Inicializa la base de datos SQLite y crea la tabla de posts vistos."""
    conn = sqlite3.connect("bot_data.db")
    conn.execute("CREATE TABLE IF NOT EXISTS seen_posts (post_id TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()


def is_new_post(post_id: str) -> bool:
    """Verifica si un post ya ha sido procesado y lo registra si es nuevo.
    
    Args:
        post_id: Identificador único del post (URL o ID del feed).
    
    Returns:
        True si el post es nuevo, False si ya fue procesado anteriormente.
    """
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


# ─────────────────────────────────────────────
# LÓGICA DE FILTRADO
# ─────────────────────────────────────────────
def clean_html(raw_html: str) -> str:
    """Limpia las etiquetas HTML de un texto y lo trunca a 300 caracteres.
    
    Args:
        raw_html: Cadena con contenido HTML a limpiar.
    
    Returns:
        Texto limpio sin etiquetas HTML, truncado a 300 caracteres si es necesario.
    """
    if not raw_html: return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = " ".join(soup.get_text().split())
    return text[:300] + "..." if len(text) > 300 else text


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@tasks.loop(minutes=CHECK_EVERY)
async def scan_feeds():
    """Tarea periódica que escanea las fuentes RSS configuradas.
    
    Ejecuta un sistema de filtros multicapa para cada post:
    - Capa 1: Elimina preguntas (terminan en ?) y ally codes
    - Capa 2: Aplica blacklist de palabras no deseadas
    - Capa 3: Valida que contenga keywords específicas de la fuente
    
    Envía un embed al canal de Discord cuando detecta un código válido.
    """
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    for source in SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries:
                entry_id = getattr(entry, "id", entry.link)
                if not is_new_post(entry_id): continue

                title_lower = entry.title.lower()

                # --- CAPA 1: FILTRO DE PREGUNTAS Y ALLY CODES ---
                if title_lower.strip().endswith("?") or "ally" in title_lower:
                    continue

                # --- CAPA 2: BLACKLIST ESTRICTA ---
                if any(b in title_lower for b in BLACKLIST):
                    continue

                # --- CAPA 3: VALIDACIÓN DE KEYWORDS ---
                # Si es Reddit, la palabra clave debe ser muy específica
                is_valid = any(k in title_lower for k in source["keywords"])
                if not is_valid:
                    continue

                # Si llegamos aquí, es un posible positivo real
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
                log.info(f"Aceptado: {entry.title}")

        except Exception as e:
            log.error(f"Error: {e}")


@bot.event
async def on_ready():
    """Handler ejecutado cuando el bot se conecta correctamente a Discord.
    
    Inicializa la base de datos y arranca el loop de escaneo de feeds si no está activo.
    """
    log.info(f"Sonda v3 activa como {bot.user}")
    init_db()
    if not scan_feeds.is_running():
        scan_feeds.start()


@bot.command()
async def estado(ctx):
    """Comando que muestra el estado operativo del bot.
    
    Args:
        ctx: Contexto del comando de Discord.
    """
    await ctx.send("🛡️ **Sonda Droid SWGoH** operando con filtros anti-AllyCode.")


if __name__ == "__main__":
    bot.run(BOT_TOKEN)