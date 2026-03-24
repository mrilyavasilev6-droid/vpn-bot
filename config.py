import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(',')))
PROVIDER_TOKEN = os.getenv('PROVIDER_TOKEN')

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

# VPN Server Settings (основной IP)
VPN_SERVER_IP = os.getenv('VPN_SERVER_IP', '87.242.86.245')

# Режим работы (False = реальный VPN)
MOCK_MODE = os.getenv('MOCK_MODE', 'True').lower() == 'true'

# ============ СПИСОК СЕРВЕРОВ MILF VPN ============
# Каждый сервер имеет свой порт, public key и short id

SERVERS = [
    {
        'name': '🇩🇪 Германия',
        'port': 443,
        'public_key': 'wjC29exW1EQR879lFUmoJS9oXfOHCjfEAQcXuH1mIn8',
        'short_id': '9ed461846d',  # первый из списка Short IDs
        'sni': 'www.cloudflare.com',
        'fingerprint': 'chrome'
    },
    {
        'name': '🇮🇳 Индия',
        'port': 444,
        'public_key': 'ngBgVGz7Q9ATfpSHC2Svpfr5I_C2Bh5eKxzovFg0MmI',
        'short_id': '004286430bfc',
        'sni': 'www.cloudflare.com',
        'fingerprint': 'chrome'
    },
    {
        'name': '🇷🇺 Россия СПБ',
        'port': 445,
        'public_key': 'TPA3ve5H4rSxWxRYIcmBsVLSzEqbPWJt_iYaCPedPiM',
        'short_id': '4415a4602b',
        'sni': 'www.cloudflare.com',
        'fingerprint': 'chrome'
    },
    {
        'name': '🇮🇹 Италия',
        'port': 446,
        'public_key': 'GI7SadleegCX9tQAKEfI7JfNVmqgLi0MYzzIr1HhJjQ',
        'short_id': 'f230491b99',
        'sni': 'www.cloudflare.com',
        'fingerprint': 'chrome'
    },
    {
        'name': '🇹🇷 Турция',
        'port': 447,
        'public_key': 'cXCztbc9yw-3kp7PWsKAQ-TiNwBLrQQznF68ic_8ljE',
        'short_id': '95',
        'sni': 'www.cloudflare.com',
        'fingerprint': 'chrome'
    },
]

# Для обратной совместимости (основной сервер - Германия)
VPN_REALITY_PUBLIC_KEY = SERVERS[0]['public_key']
VPN_REALITY_SHORT_ID = SERVERS[0]['short_id']
VPN_REALITY_SNI = SERVERS[0]['sni']
