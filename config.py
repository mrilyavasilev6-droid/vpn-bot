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

# VPN Server Settings
VPN_SERVER_IP = os.getenv('VPN_SERVER_IP')
VPN_REALITY_PUBLIC_KEY = os.getenv('VPN_REALITY_PUBLIC_KEY')
VPN_REALITY_SHORT_ID = os.getenv('VPN_REALITY_SHORT_ID')
VPN_REALITY_SNI = os.getenv('VPN_REALITY_SNI', 'www.cloudflare.com')

# Mode
MOCK_MODE = os.getenv('MOCK_MODE', 'True').lower() == 'true'
