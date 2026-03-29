# Sonda Droid - Bot de Discord para SWGoH

Bot de Discord que monitoriza fuentes RSS para detectar automáticamente códigos regalo, códigos promo y compensaciones de Star Wars: Galaxy of Heroes.

## Características

- **Monitorización en tiempo real**: Escanea Reddit y foros oficiales de EA cada 15 minutos
- **Filtros multicapa**: Sistema de 3 capas para eliminar falsos positivos
- **Anti-spam**: Elimina preguntas, ally codes y contenido no relacionado
- **Embeds automáticos**: Notificaciones ricas en formato Discord
- **Persistencia**: Base de datos SQLite para evitar duplicados

## Fuentes Monitorizadas

1. Reddit r/SWGalaxyOfHeroes (filtrado por: "promo code", "gift code", "redeem", "free gift", "active code")
2. Foros oficiales de EA (filtrado por: "compensation", "gift", "make-good", "webstore", "free")

## Requisitos

- Python 3.12+
- Discord Bot Token
- Cuenta de Discord con permisos para crear un bot

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

## Despliegue en Oracle Cloud (Free Tier)

El bot está diseñado para desplegarse en la capa gratuita de Oracle Cloud Infrastructure (OCI).

### Configuración en Oracle Cloud

1. **Crear una cuenta** en [oracle.com/cloud/free](https://www.oracle.com/cloud/free/)

2. **Crear una instancia**:
   - Ve a Compute > Instances
   - Crea una nueva instancia con:
     - Imagen: Oracle Linux 8 o Ubuntu
     - Forma: VM.Standard.E2.1.Micro (Always Free)
     - Clave SSH: Genera un par de claves SSH

3. **Configurar el firewall**:
   ```bash
   sudo firewall-cmd --permanent --add-port=22/tcp
   sudo firewall-cmd --reload
   ```

### Preparar el servidor

1. Conectar por SSH:
   ```bash
   ssh -i clave_privada opc@<ip-publica>
   ```

2. Instalar UV:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc
   ```

3. Instalar Python (si no está):
   ```bash
   sudo dnf install python3.12 python3.12-venv git -y  # Oracle Linux
   # sudo apt install python3.12 python3.12-venv git -y  # Ubuntu
   ```

4. Clonar el repositorio:
   ```bash
   git clone <repositorio>
   cd probe-droid-swgoh-bot
   ```

5. Configurar variables de entorno:
   ```bash
   cp .env.example .env
   nano .env
   ```

### Ejecutar el bot como servicio

Crear servicio systemd para que el bot se reinicie automáticamente:

```bash
sudo nano /etc/systemd/system/sondadroid.service
```

Contenido del servicio:
```ini
[Unit]
Description=Sonda Droid SWGoH Bot
After=network.target

[Service]
Type=simple
User=opc
WorkingDirectory=/home/opc/probe-droid-swgoh-bot
ExecStart=/home/opc/.local/bin/uv run python bot.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Iniciar el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sondadroid
sudo systemctl start sondadroid
```

Verificar estado:
```bash
sudo systemctl status sondadroid
```

Ver logs:
```bash
sudo journalctl -u sondadroid -f
```

### Actualizar el bot

```bash
cd probe-droid-swgoh-bot
git pull
sudo systemctl restart sondadroid
```

## Configuración

Crear archivo `.env` en la raíz del proyecto:

```env
BOT_TOKEN=tu_token_de_bot_aqui
CHANNEL_ID=id_del_canal_de_discord
```

### Obtener el Token del Bot

1. Ve a [Discord Developer Portal](https://discord.com/developers/applications)
2. Crea una nueva aplicación
3. Ve a "Bot" y crea un bot
4. Copia el token
5. En "Privileged Gateway Intents", habilita **Message Content Intent**

### Obtener el Channel ID

1. En Discord, habilita el "Developer Mode" (Configuración > Avanzado > Modo Desarrollador)
2. Haz clic derecho en el canal > "Copiar ID del canal"

## Uso

Iniciar el bot:
```bash
python bot.py
```

## Comandos

| Comando | Descripción |
|---------|-------------|
| `!estado` | Muestra el estado operativo del bot |

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
├── pyproject.toml      # Configuración del proyecto
├── .env                # Variables de entorno (no comprometido)
├── bot_data.db         # Base de datos SQLite (auto-generado)
└── bot.log             # Log del bot (auto-generado)
```

## Contribuir

1. Haz un fork del repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-feature`)
3. Commit tus cambios (`git commit -m 'Añadir nueva feature'`)
4. Push a la rama (`git push origin feature/nueva-feature`)
5. Abre un Pull Request

## Licencia

MIT License
