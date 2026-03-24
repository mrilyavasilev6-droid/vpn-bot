import aiohttp
import json
import uuid
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class XUIClient:
    """Клиент для работы с 3x-ui API"""

    def __init__(self, api_url: str, username: str, password: str):
        self.api_url = api_url.rstrip('/')
        self.username = username
        self.password = password
        self._session = None
        self._cookies = None
        self._inbound_id = 1  # ID инбаунда (у вас 1)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _login(self) -> bool:
        """Авторизация в панели"""
        session = await self._get_session()
        
        data = {"username": self.username, "password": self.password}
        
        async with session.post(f"{self.api_url}/login", data=data) as resp:
            logger.info(f"Login response status: {resp.status}")
            
            if resp.status == 200:
                self._cookies = resp.cookies
                logger.info("✅ Logged in to 3x-ui")
                return True
            else:
                text = await resp.text()
                logger.error(f"Login failed: {resp.status}, response: {text}")
                return False

    async def _request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Выполнить запрос к API"""
        session = await self._get_session()
        
        # Если нет cookies, логинимся
        if not self._cookies:
            logger.info("No cookies, logging in...")
            await self._login()
            if not self._cookies:
                logger.error("Failed to login")
                return None
        
        # Формируем заголовки
        headers = {}
        if self._cookies:
            headers["Cookie"] = self._cookies.output(header='')
        
        async with session.request(method, f"{self.api_url}{endpoint}", json=data, headers=headers) as resp:
            if resp.status == 401:
                # Перелогиниваемся
                logger.info("Got 401, re-logging...")
                await self._login()
                if self._cookies:
                    headers["Cookie"] = self._cookies.output(header='')
                async with session.request(method, f"{self.api_url}{endpoint}", json=data, headers=headers) as resp2:
                    if resp2.status == 200:
                        return await resp2.json()
                    return None
            elif resp.status == 200:
                return await resp.json()
            else:
                logger.error(f"Request failed: {resp.status}")
                return None

    async def add_client(self, days: int = 30, email: str = None) -> Optional[str]:
        """Создать нового клиента на сервере"""
        logger.info(f"add_client called with days={days}, email={email}")
        
        client_uuid = str(uuid.uuid4())
        expire_timestamp = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
        
        if not email:
            email = f"user_{client_uuid[:8]}"
        
        payload = {
            "id": self._inbound_id,
            "settings": json.dumps({
                "clients": [{
                    "id": client_uuid,
                    "email": email,
                    "expireTime": expire_timestamp,
                    "enable": True,
                    "flow": "xtls-rprx-vision",
                    "limitIp": 1,
                    "totalGB": 0
                }]
            })
        }
        
        logger.info(f"Sending payload to {self.api_url}/panel/api/inbounds/addClient")
        
        result = await self._request('POST', '/panel/api/inbounds/addClient', payload)
        
        logger.info(f"Add client result: {result}")
        
        if result and result.get('success'):
            logger.info(f"✅ Client created: {client_uuid}")
            return client_uuid
        
        logger.error(f"❌ Failed to create client: {result}")
        return None

    async def delete_client(self, client_uuid: str) -> bool:
        """Удалить клиента"""
        payload = {"id": self._inbound_id, "clientId": client_uuid}
        result = await self._request('POST', '/panel/api/inbounds/delClient', payload)
        
        if result and result.get('success'):
            logger.info(f"✅ Client deleted: {client_uuid}")
            return True
        
        logger.error(f"❌ Failed to delete client: {result}")
        return False

    async def get_client(self, client_uuid: str) -> Optional[Dict]:
        """Получить информацию о клиенте"""
        result = await self._request('GET', f'/panel/api/inbounds/getClientTraffic?id={client_uuid}')
        
        if result and result.get('success') and result.get('obj'):
            return result['obj']
        return None

    async def enable_client(self, client_uuid: str, enable: bool = True) -> bool:
        """Включить/отключить клиента"""
        payload = {"id": self._inbound_id, "clientId": client_uuid, "enable": enable}
        result = await self._request('POST', '/panel/api/inbounds/clientStatus', payload)
        return result and result.get('success', False)

    async def get_client_config(
        self, 
        client_uuid: str, 
        server_host: str, 
        plan_name: str,
        public_key: str = None,
        short_id: str = None,
        sni: str = None
    ) -> str:
        """Сгенерировать vless:// ссылку для подключения"""
        from config import VPN_REALITY_PUBLIC_KEY, VPN_REALITY_SHORT_ID, VPN_REALITY_SNI
        
        pbk = public_key or VPN_REALITY_PUBLIC_KEY
        sid = short_id or VPN_REALITY_SHORT_ID
        sni_value = sni or VPN_REALITY_SNI or "www.cloudflare.com"
        
        name = urllib.parse.quote(plan_name)
        
        return (
            f"vless://{client_uuid}@{server_host}:443"
            f"?type=tcp&security=reality"
            f"&pbk={pbk}&fp=chrome"
            f"&sni={sni_value}&sid={sid}"
            f"#{name}"
        )

    async def close(self):
        if self._session:
            await self._session.close()
