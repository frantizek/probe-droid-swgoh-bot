# Sonda Droid - Bot de Discord para SWGoH

Bot de Discord que monitoriza fuentes RSS para detectar automáticamente códigos regalo, códigos promo y compensaciones de Star Wars: Galaxy of Heroes. Además, publica órdenes de Batalla Territorial (BT) desde MongoDB.

## Características

- **Monitorización en tiempo real**: Escanea Reddit y foros oficiales de EA cada 15 minutos
- **Filtros multicapa**: Sistema de 3 capas para eliminar falsos positivos
- **Anti-spam**: Elimina preguntas, ally codes y contenido no relacionado
- **Embeds automáticos**: Notificaciones ricas en formato Discord
- **Persistencia**: Base de datos SQLite para evitar duplicados
- **Órdenes BT**: Publicación automática diaria (17:00 UTC) de órdenes de Batalla Territorial desde MongoDB
- **Soporte GT**: Estructura de datos preparada para Guerra Territorial (4 fases: signup, defensas, ataque, cierre)
- **Comandos admin**: `!set_bt_date` y `!orden` para gestión de BT

## Fuentes Monitorizadas

1. Reddit r/SWGalaxyOfHeroes (filtrado por: "promo code", "gift code", "redeem", "free gift", "active code")
2. Foros oficiales de EA (filtrado por: "compensation", "gift", "make-good", "webstore", "free")

## Requisitos

- Python 3.12+
- Discord Bot Token
- Cuenta de Discord con permisos para crear un bot
- MongoDB Atlas (para órdenes de gremio)

## Instalación

### Usando UV (Recomendado)

1. Clonar el repositorio:
```bash
git clone <repositorio>
cd probe-droid-swgoh-bot
```

2. Instalar dependencias con UV:
```bash
uv sync
```

UV instalará automáticamente Python si no está disponible y creará el entorno virtual.

### Usando pip tradicional

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## Configuración

Crear archivo `.env` en la raíz del proyecto:

```env
BOT_TOKEN=tu_token_de_bot_aqui
GENERAL_CHANNEL_ID=id_del_canal_general
CODE_ALERTS_CHANNEL_ID=id_del_canal_de_codigos
BT_GUILD_ORDERS_CHANNEL_ID=id_del_canal_de_ordenes_bt
GT_GUILD_ORDERS_CHANNEL_ID=id_del_canal_de_ordenes_gt
MONGODB_URI=tu_mongodb_uri
MONGODB_DB_NAME=orders_manager
```

### Variables de Entorno

| Variable | Requerido | Descripción |
|----------|-----------|-------------|
| `BOT_TOKEN` | Sí | Token del bot de Discord |
| `GENERAL_CHANNEL_ID` | No | Canal por defecto (fallback para los demás) |
| `CODE_ALERTS_CHANNEL_ID` | No | Canal para alertas RSS de códigos (default: GENERAL_CHANNEL_ID) |
| `BT_GUILD_ORDERS_CHANNEL_ID` | No | Canal para órdenes de BT (default: GENERAL_CHANNEL_ID) |
| `GT_GUILD_ORDERS_CHANNEL_ID` | No | Canal para órdenes de GT (default: GENERAL_CHANNEL_ID) |
| `MONGODB_URI` | Sí | URI de conexión a MongoDB |
| `MONGODB_DB_NAME` | No | Nombre de la base de datos (default: `orders_manager`) |

### Obtener el Token del Bot

1. Ve a [Discord Developer Portal](https://discord.com/developers/applications)
2. Crea una nueva aplicación
3. Ve a "Bot" y crea un bot
4. Copia el token
5. En "Privileged Gateway Intents", habilita **Message Content Intent**

### Obtener el Channel ID

1. En Discord, habilita el "Developer Mode" (Configuración > Avanzado > Modo Desarrollador)
2. Haz clic derecho en el canal > "Copiar ID del canal"

### Autorización

Los comandos admin (`!set_bt_date`, `!orden`) están disponibles para usuarios con los siguientes permisos en el servidor: **Administrador**, **Gestionar Servidor**, **Expulsar Miembros** o **Banear Miembros** (cubren perfiles de admin y oficial).

## Comandos

| Comando | Admin | Descripción |
|---------|-------|-------------|
| `!estado` | No | Muestra el estado operativo del bot y configuración BT/GT |
| `!set_bt_date YYYY-MM-DD` | Sí | Configura la fecha de inicio de la BT |
| `!set_gt_date YYYY-MM-DD` | Sí | Configura la fecha de inicio de la GT |
| `!orden_bt <1-6>` | Sí | Publica la orden BT de una fase específica |
| `!orden_bt` | Sí | Publica la orden BT de la fase actual |
| `!orden_gt <0-3>` | Sí | Publica la orden GT de una fase específica |
| `!orden_gt` | Sí | Publica la orden GT de la fase actual |

## Órdenes de Batalla Territorial (BT)

El bot publica automáticamente las órdenes de BT cada día a las **17:00 UTC** y las de GT a las **19:00 UTC** en sus respectivos canales configurados.

### Flujo de publicación

1. El admin configura la fecha de inicio de BT con `!set_bt_date 2026-07-06`
2. El bot calcula la fase actual: `días desde inicio + 1`
3. Busca en MongoDB un documento activo en la colección `orders` con el `template_id` correspondiente:

   | Fase | template_id |
   |------|-------------|
   | 1 | `ordenes_fase_1` |
   | 2 | `ordenes_fase_2` |
   | 3 | `ordenes_fase_3` |
   | 4 | `ordenes_fase_4` |
   | 5 | `ordenes_fase_5_mandalore` |
   | 6 | `ordenes_fase_6_mandalore` |

4. Publica un embed con el formato: `"MIÉRCOLES 8 de Julio:\n\n{content}"`

### Publicación manual

Un admin puede forzar la publicación con:
- `!orden` — publica la fase actual
- `!orden 3` — publica la fase 3 específica

## Guerra Territorial (GT) — Preparación

La estructura de datos para GT está definida con 4 fases y un script para inicializar los documentos en MongoDB:

| Fase | template_id | Descripción |
|:----:|-------------|-------------|
| 0 | `ordenes_gt_signup` | Apuntarse a la batalla |
| 1 | `ordenes_gt_defensas` | Instrucciones de defensa por zona |
| 2 | `ordenes_gt_ataque` | Instrucciones de ataque |
| 3 | `ordenes_gt_cierre` | Cierre y resultados |

> Para crear los documentos en MongoDB usa el script desde el otro bot o directamente desde MongoDB Atlas. La publicación automática de GT se realiza cada día a las **19:00 UTC** (2 horas después que BT).

## Despliegue en Oracle Cloud (Free Tier)

El bot está diseñado para desplegarse en la capa gratuita de Oracle Cloud Infrastructure (OCI).

### Configuración en Oracle Cloud

1. **Crear una cuenta** en [oracle.com/cloud/free](https://www.oracle.com/cloud/free/)

2. **Crear una instancia**:
   - Ve a Compute > Instances
   - Crea una nueva instancia con:
     - Imagen: Ubuntu 22.04+
     - Forma: VM.Standard.E2.1.Micro (Always Free)
     - Clave SSH: Genera un par de claves SSH

### Preparar el servidor

1. Conectar por SSH:
   ```bash
   ssh ubuntu@<ip-publica>
   ```

2. Instalar UV:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc
   ```

3. Clonar el repositorio:
   ```bash
   mkdir -p /opt/bots/discord
   cd /opt/bots/discord
   git clone <repositorio>
   cd probe-droid-swgoh-bot
   ```

4. Configurar variables de entorno:
   ```bash
   cp .env.example .env
   nano .env
   ```

### Ejecutar el bot como servicio

Crear servicio systemd:

```bash
sudo nano /etc/systemd/system/probe-droid.service
```

Contenido del servicio:
```ini
[Unit]
Description=Probe Droid - Discord bot for SWGOH
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/bots/discord/probe-droid-swgoh-bot
ExecStart=/home/ubuntu/.local/bin/uv run python bot.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Iniciar el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable probe-droid
sudo systemctl start probe-droid
```

Verificar estado:
```bash
sudo systemctl status probe-droid
```

Ver logs:
```bash
sudo journalctl -u probe-droid -f
```

### Actualizar el bot

```bash
cd /opt/bots/discord/probe-droid-swgoh-bot
git pull
sudo systemctl restart probe-droid
```

## Sistema de Filtros

El bot utiliza un sistema de 3 capas para filtrar posts:

### Capa 1: Filtro Básico
- Elimina preguntas (títulos que terminan en `?`)
- Elimina posts que contienen "ally" (ally codes)

### Capa 2: Blacklist
Palabras que siempre descartan un post:
- ally code, friend code, add me, roster
- how, help, issue, error, missing, question
- starkiller, lsb, bundle, purchase, support, banned, cheat

### Capa 3: Keywords
Cada fuente tiene palabras clave específicas que deben estar presentes para considerarlo válido.

## Estructura del Proyecto

```
probe-droid-swgoh-bot/
├── bot.py              # Código principal del bot
├── pyproject.toml      # Configuración del proyecto y dependencias
├── .env                # Variables de entorno (no comprometido)
├── .env.example        # Plantilla de variables de entorno
├── bot_data.db         # Base de datos SQLite (auto-generado)
├── bot.log             # Log del bot (auto-generado)
└── .github/
    ├── ISSUE_TEMPLATE/ # Plantillas para issues
    └── pull_request_template.md
```

## Pruebas

El proyecto usa `pytest` para las pruebas unitarias.

```bash
# Instalar dependencias de desarrollo
uv sync --extra dev

# Ejecutar todas las pruebas
uv run pytest -v

# Ejecutar con salida resumida
uv run pytest --tb=short
```

Las pruebas de base de datos usan archivos temporales y no afectan la base de datos de producción.

## Contribuir

1. Documenta el issue en `.github/ISSUE_TEMPLATE/` o crea un archivo de especificación
2. Crea una rama para tu feature (`git checkout -b feat/nombre-feature`)
3. Commit tus cambios (`git commit -m "feat: descripción del cambio"`)
4. Push a la rama (`git push origin feat/nombre-feature`)
5. Abre un Pull Request usando la plantilla

## Licencia

MIT License
