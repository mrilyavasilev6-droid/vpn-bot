import aiohttp
from datetime import datetime, timedelta
from config import MARZBAN_URL, MARZBAN_USERNAME, MARZBAN_PASSWORD

class MarzbanAPI:
    def __init__(self):
        self.base_url = MARZBAN_URL.rstrip('/')
        self.auth = aiohttp.BasicAuth(MARZBAN_USERNAME, MARZBAN_PASSWORD)
    
    async def create_user(self, username: str, expire_days: int = 30, data_limit_gb: int = 0):
        """Создание пользователя в Marzban"""
        url = f"{self.base_url}/api/user"
        expire_timestamp = int((datetime.now() + timedelta(days=expire_days)).timestamp())
        
        payload = {
            "username": username,
            "proxies": {"vless": {}, "vmess": {}, "trojan": {}, "shadowsocks": {}},
            "expire": expire_timestamp,
            "data_limit": data_limit_gb * 1024 * 1024 * 1024 if data_limit_gb > 0 else 0,
            "status": "active",
            "inbounds": {
                "vless": ["VLESS TCP REALITY"],
                "vmess": ["VMESS TCP NOTLS"],
                "trojan": ["TROJAN TCP NOTLS"],
                "shadowsocks": ["Shadowsocks TCP"]
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, auth=self.auth) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                raise Exception(f"Marzban API error: {resp.status}")
    
    async def get_user_info(self, username: str):
        """Получение информации о пользователе"""
        url = f"{self.base_url}/api/user/{username}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=self.auth) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    
    async def get_subscription_link(self, username: str) -> str:
        """Получение ссылки на подписку"""
        url = f"{self.base_url}/api/user/{username}/subscription"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=self.auth) as resp:
                if resp.status == 200:
                    return await resp.text()
                return None
