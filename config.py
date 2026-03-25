import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(',')))
PROVIDER_TOKEN = os.getenv('PROVIDER_TOKEN')

# Database
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'vpn_bot'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASS', 'password')
    }
    DATABASE_URL = f"postgresql+asyncpg://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# 3x-ui Panel Settings
XUI_HOST = os.getenv('XUI_HOST')
XUI_USERNAME = os.getenv('XUI_USERNAME')
XUI_PASSWORD = os.getenv('XUI_PASSWORD')

# Mode
MOCK_MODE = os.getenv('MOCK_MODE', 'True').lower() == 'true'

# ============ VPN Server Configuration ============
# Общий UUID для всех серверов
SERVER_UUID = "e869ec05-b749-41fb-9b25-49257cc1e7df"

# IP или домен сервера (для подписки)
VPN_SERVER_IP = os.getenv('VPN_SERVER_IP', 'panel.3utilities.com')

# Список серверов с их параметрами
SERVERS = [
    {
        "name": "🇩🇪 Германия",
        "port": 443,
        "public_key": "yv6b4Q9VopGCLI0JLaOVtVJZ8PovFE3sO31bPhbgX4",
        "short_id": "8f3512"
    },
    {
        "name": "🇮🇳 Индия",
        "port": 444,
        "public_key": "rW97vS_cCKklOO1IFiL5VvVB5uTMtBP2h2o7YhijcIk",
        "short_id": "8d"
    },
    {
        "name": "🇷🇺 Россия",
        "port": 445,
        "public_key": "czaIL8FZPaoYXIsZfc6G6grhG8E3cwMtUg7r21TELyA",
        "short_id": "afd9532e1e0f"
    },
    {
        "name": "🇮🇹 Италия",
        "port": 446,
        "public_key": "rRRlWdFOietYDQjBiLR-wsaoTntU0n_yNdZxufDQDY",
        "short_id": "6c6ee21d2a8a"
    },
    {
        "name": "🇹🇷 Турция",
        "port": 447,
        "public_key": "BbCdEbN_BIxQAE2ui80nF6JqMBs8UcVCr-93KQP9aiA",
        "short_id": "e2cbc0e1"
    }
]

# Ссылка-подписка (единая для всех серверов)
SUBSCRIPTION_URL = "http://panel.3utilities.com:2096/sub/milf_vpn_sub"

# Reality общие настройки
REALITY_SNI = "www.cloudflare.com"
REALITY_FINGERPRINT = "chrome"
REALITY_TYPE = "tcp"
REALITY_SECURITY = "reality"
