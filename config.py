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

# Marzban API Settings
MARZBAN_URL = os.getenv('MARZBAN_URL', 'https://vpn.olin.mooo.com/api')
MARZBAN_USERNAME = os.getenv('MARZBAN_USERNAME', 'admin')
MARZBAN_PASSWORD = os.getenv('MARZBAN_PASSWORD', 'admin')

# Mode
MOCK_MODE = os.getenv('MOCK_MODE', 'False').lower() == 'true'

# Subscription URL (единая подписка из Marzban)
SUBSCRIPTION_URL = os.getenv('SUBSCRIPTION_URL', 'https://vpn.olin.mooo.com/sub/')
