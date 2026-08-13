# Sonda Droid - Bot de Discord para SWGoH

Bot de Discord que monitoriza fuentes RSS para detectar automáticamente códigos regalo, códigos promo y compensaciones de Star Wars: Galaxy of Heroes. Además, publica órdenes de Batalla Territorial (BT) y Guerra Territorial (GT) desde MongoDB.

## Características

- **Monitorización en tiempo real**: Escanea Reddit y foros oficiales de EA cada 15 minutos
- **Filtros multicapa**: Sistema de 3 capas para eliminar falsos positivos
- **Anti-spam**: Elimina preguntas, ally codes y contenido no relacionado
- **Embeds automáticos**: Notificaciones ricas en formato Discord
- **Persistencia**: Base de datos SQLite para evitar duplicados
- **Órdenes BT**: Publicación automática diaria (17:00 UTC) de órdenes de Batalla Territorial desde MongoDB
- **Órdenes GT**: Publicación automática diaria (18:00 UTC) de órdenes de Guerra Territorial desde MongoDB
- **Avisos territoriales automáticos**: Modo auto (`!avisos_territoriales`) que calcula el ciclo oficial de 14 días (6 días BT + 4 días GT#1 + 4 días GT#2) sin alimentar fechas manuales
- **Comandos admin**: `!avisos_territoriales`, `!set_bt_date`, `!set_gt_date`, `!orden_bt` y `!orden_gt` para gestión de BT y GT

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
ADMIN_USER_IDS=id_usuario_discord,otro_id_usuario
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
| `ADMIN_USER_IDS` | No | IDs de Discord (separados por coma) autorizados a usar comandos admin por MD (default: vacío) |

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

Los comandos admin (`!avisos_territoriales`, `!set_bt_date`, `!set_gt_date`, `!orden_bt`, `!orden_gt`) están disponibles para usuarios con los siguientes permisos en el servidor: **Administrador**, **Gestionar Servidor**, **Expulsar Miembros** o **Banear Miembros** (cubren perfiles de admin y oficial). También funcionan por MD para los IDs de Discord incluidos en `ADMIN_USER_IDS`.

## Comandos

| Comando | Admin | Descripción |
|---------|-------|-------------|
| `!estado` | No | Muestra el estado operativo del bot y configuración BT/GT |
| `!ayuda` | Sí | Muestra los comandos disponibles |
| `!avisos_territoriales` | Sí | Muestra el estado del modo automático de avisos territoriales |
| `!avisos_territoriales iniciar [YYYY-MM-DD]` | Sí | Activa los avisos automáticos (ancla: fecha indicada, fecha de BT guardada o lunes más reciente) |
| `!avisos_territoriales detener` | Sí | Detiene los avisos automáticos |
| `!set_bt_date YYYY-MM-DD` | Sí | Configura la fecha de inicio de la BT (solo con modo auto detenido) |
| `!set_gt_date YYYY-MM-DD` | Sí | Configura la fecha de inicio de la GT (solo con modo auto detenido) |
| `!orden_bt <1-6>` | Sí | Publica la orden BT de una fase específica |
| `!orden_bt` | Sí | Publica la orden BT de la fase actual |
| `!orden_gt <0-3>` | Sí | Publica la orden GT de una fase específica |
| `!orden_gt` | Sí | Publica la orden GT de la fase actual |

## Órdenes de Batalla Territorial (BT)

El bot publica automáticamente las órdenes de BT a las **17:00 UTC** y las de GT a las **18:00 UTC** en sus respectivos canales configurados.

### Flujo de publicación (modo manual)

> Con el **modo auto** activado (`!avisos_territoriales iniciar`) el bot deriva las fases del ciclo de 14 días y no hace falta configurar fechas. El flujo siguiente es para el modo manual (modo auto detenido).

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
- `!orden_bt` / `!orden_gt` — publica la fase actual
- `!orden_bt 3` — publica la fase 3 de BT específica
- `!orden_gt 0` — publica la fase 0 de GT específica (signup)

## Guerra Territorial (GT) — Ciclo de 14 días

La GT sigue el **ciclo oficial de 14 días** de EA junto con la BT: 6 días de BT + 4 días de GT#1 + 4 días de GT#2, sin solapamiento. El ancla del ciclo es el **lunes de inicio de la BT**.

### Modo automático (recomendado)

Con `!avisos_territoriales iniciar [YYYY-MM-DD]` el bot activa los avisos automáticos y calcula cada día la fase correspondiente con `(hoy - ancla) % 14`, sin que el admin tenga que alimentar fechas. El ancla se guarda en SQLite y el ciclo avanza solo cada 14 días.

- Se usa la fecha indicada, la **fecha de BT guardada** o el **lunes más reciente** como ancla, siempre alineado al lunes (día de inicio de BT).
- Se toma la BT **previa** como referencia, de modo que no quedan días sin publicación (ej.: con ancla lunes 03/08, el miércoles 12/08 es GT#1 cierre y el jueves 13/08 GT#2 signup).
- `!avisos_territoriales detener` vuelve al modo manual. Mientras el modo auto esté activo, `!set_bt_date` y `!set_gt_date` se ignoran con un aviso.

### Fases del ciclo

| Día | Semana | Evento | Fase | template_id |
|:--:|:--:|:--:|:--:|-------------|
| 0 | Lunes | BT | 1 | `ordenes_fase_1` |
| 1 | Martes | BT | 2 | `ordenes_fase_2` |
| 2 | Miércoles | BT | 3 | `ordenes_fase_3` |
| 3 | Jueves | BT | 4 | `ordenes_fase_4` |
| 4 | Viernes | BT | 5 | `ordenes_fase_5_mandalore` |
| 5 | Sábado | BT | 6 | `ordenes_fase_6_mandalore` |
| 6 | Domingo | GT#1 | 0 signup | `ordenes_gt_signup` |
| 7 | Lunes | GT#1 | 1 defensas | `ordenes_gt_defensas` |
| 8 | Martes | GT#1 | 2 ataque | `ordenes_gt_ataque` |
| 9 | Miércoles | GT#1 | 3 cierre | `ordenes_gt_cierre` |
| 10 | Jueves | GT#2 | 0 signup | `ordenes_gt_signup` |
| 11 | Viernes | GT#2 | 1 defensas | `ordenes_gt_defensas` |
| 12 | Sábado | GT#2 | 2 ataque | `ordenes_gt_ataque` |
| 13 | Domingo | GT#2 | 3 cierre | `ordenes_gt_cierre` |

> La fase 3 (cierre/review) **sí se publica**; el contenido depende del template en MongoDB.

### Modo manual (fallback)

Con el modo auto detenido, `!set_gt_date YYYY-MM-DD` fija la fecha de inicio y la GT queda activa durante una ventana según el día de la semana:

- **Domingo** → ventana de **7 días** (cubre la semana completa con 2 GT)
- **Jueves** → ventana de **3 días** (una GT)
- **Otro día** → se muestra advertencia y la ventana es de 3 días

Dentro de la ventana las fases siguen el día de la semana: signup (domingo/jueves), defensas (lunes/viernes), ataque (martes/sábado) y cierre (miércoles/domingo).

> Para crear los documentos en MongoDB usa el script desde el otro bot o directamente desde MongoDB Atlas. La publicación automática de GT se realiza cada día a las **18:00 UTC**.

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

### Actualizar el bot (guía rápida de despliegue)

Secuencia completa para desplegar la última versión de `main` en la VM:

```bash
# 1. Conectar a la VM (desde tu máquina local)
ssh ubuntu@<ip-publica>

# 2. Ir al directorio del bot
cd /opt/bots/discord/probe-droid-swgoh-bot

# 3. Comprobar que no hay cambios locales sin commitear
#    (debe salir vacío; bot_data.db y bot.log no aparecen por estar en .gitignore)
git status --short

# 4. Traer la última versión de main (fast-forward evita merge commits accidentales)
git pull --ff-only

# 5. Si cambió pyproject.toml o uv.lock, resincronizar dependencias
#    (hacerlo siempre es rápido y seguro)
uv sync

# 6. Reiniciar el servicio con la nueva versión
sudo systemctl restart probe-droid

# 7. Confirmar que el servicio está activo (debe mostrar "active (running)")
sudo systemctl status probe-droid

# 8. Ver logs de arranque
sudo journalctl -u probe-droid --since "5 min ago"
#    Para seguir los logs en vivo: sudo journalctl -u probe-droid -f
```

**Qué debe aparecer en los logs para confirmar un arranque correcto:**

- `Shard ID None has connected to Gateway`
- `[INFO] Sonda v5 activa como probe-droid-swgoh-bot#2600`
- `[INFO] RSS scan: cada 15 min | BT daily: 17:00 UTC | GT daily: 18:00 UTC`

**Mensajes normales que NO son errores:**

- `probe-droid.service: Main process exited, code=exited, status=143/n/a` → cierre correcto por `restart` (SIGTERM)
- `[WARNING] PyNaCl is not installed, voice will NOT be supported` (y el de `davey`) → voz no soportada, sin efecto

**Verificación final en Discord:** ejecutar `!estado` (debe mostrar BT y GT configurados con sus horarios).

**Rollback (volver a una versión anterior):**

```bash
# Ver las últimas versiones de main y elegir un commit anterior
git log --oneline -5
git reset --hard <commit_id>    # ¡OJO! descarta cualquier cambio local
sudo systemctl restart probe-droid
# Para volver al estado normal después del rollback:
git pull --ff-only
```

## Sistema de Filtros

El bot utiliza un sistema de 3 capas para filtrar posts:

### Capa 1: Filtro Básico
- Elimina preguntas (títulos que terminan en `?`)
- Elimina posts que contienen "ally" (ally codes)

### Capa 2: Blacklist
Palabras que siempre descartan un post:
- ally code, allycode, friend code, my code, add me, roster
- how, help, issue, error, missing, question, ?, why
- starkiller, lsb, bundle, purchase, support, banned, cheat

### Capa 3: Keywords
Cada fuente tiene palabras clave específicas que deben estar presentes para considerarlo válido.

## Estructura del Proyecto

```
probe-droid-swgoh-bot/
├── bot.py              # Código principal del bot
├── AGENTS.md           # Acuerdo de trabajo del agente (workflow)
├── pyproject.toml      # Configuración del proyecto y dependencias
├── tests/              # Pruebas unitarias (pytest)
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
