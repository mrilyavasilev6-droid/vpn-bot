import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# Payments
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")

# Marzban API
MARZBAN_URL = os.getenv("MARZBAN_URL", "http://localhost:8000/api")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME", "admin")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD", "admin")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./vpn_bot.db")

# VPN Settings (для совместимости со старым кодом)
VPN_SERVER_IP = os.getenv("VPN_SERVER_IP", "87.242.86.245")
XUI_HOST = os.getenv("XUI_HOST", "")
XUI_USERNAME = os.getenv("XUI_USERNAME", "")
XUI_PASSWORD = os.getenv("XUI_PASSWORD", "")
SUBSCRIPTION_URL = os.getenv("SUBSCRIPTION_URL", "http://87.242.86.245:8000/sub/")
REALITY_SNI = os.getenv("REALITY_SNI", "yahoo.com")
REALITY_FINGERPRINT = os.getenv("REALITY_FINGERPRINT", "chrome")
MOCK_MODE = os.getenv("MOCK_MODE", "False").lower() == "true"

# Servers list
SERVERS = [
    {"name": "🇩🇪 Germany", "port": 443, "public_key": "", "short_id": ""},
    {"name": "🇮🇳 India", "port": 443, "public_key": "", "short_id": ""},
    {"name": "🇷🇺 Russia", "port": 443, "public_key": "", "short_id": ""},
]
