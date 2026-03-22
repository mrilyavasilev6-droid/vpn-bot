import aiohttp
import json
from datetime import datetime, timedelta
import os

MOCK_MODE = os.getenv('MOCK_MODE', 'True').lower() == 'true'

class XUIClient:
    def __init__(self, api_url, username, password):
        self.api_url = api_url.rstrip('/')
        self.username = username
        self.password = password
        self.cookie = None

    async def _request(self, method, endpoint, data=None):
        if MOCK_MODE:
            return {"success": True, "mock": True}
        async with aiohttp.ClientSession() as session:
            if not self.cookie:
                # Логин
                async with session.post(f"{self.api_url}/login", data={"username": self.username, "password": self.password}) as resp:
                    if resp.status == 200:
                        self.cookie = resp.cookies
            headers = {}
            if self.cookie:
                headers["Cookie"] = self.cookie.output(header='')
            async with session.request(method, f"{self.api_url}{endpoint}", json=data, headers=headers) as resp:
                return await resp.json()

    async def add_client(self, days):
        if MOCK_MODE:
            return f"mock_client_{datetime.now().timestamp()}"
        email = f"user_{datetime.now().timestamp()}"
        expire = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
        payload = {
            "id": 1,  # ID инбаунда (должен существовать)
            "settings": json.dumps({
                "clients": [{
                    "email": email,
                    "expireTime": expire,
                    "enable": True,
                    "flow": "xtls-rprx-vision",
                    "limitIp": 1,
                    "totalGB": 0
                }]
            })
        }
        resp = await self._request('POST', '/panel/api/inbounds/addClient', payload)
        if resp.get('success'):
            return email
        return None

    async def delete_client(self, client_id):
        if MOCK_MODE:
            return True
        resp = await self._request('POST', f'/panel/api/inbounds/delClient/{client_id}')
        return resp.get('success', False)

    async def get_client_config(self, client_id):
        if MOCK_MODE:
            return f"[Interface]\nPrivateKey = mock_{client_id}\nAddress = 10.0.0.2/24\nDNS = 1.1.1.1"
        # Здесь нужно реализовать получение конфига из панели
        return f"Конфиг для {client_id} (заглушка)"
