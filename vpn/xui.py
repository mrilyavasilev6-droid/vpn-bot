import aiohttp
import json
import uuid
import urllib.parse
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
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
        self._inbound_id = 1  # ID инбаунда (основной, для создания клиентов)
        logger.info(f"XUIClient initialized with api_url: {self.api_url}")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _login(self) -> bool:
        """Авторизация в панели"""
        session = await self._get_session()
        
        data = {"username": self.username, "password": self.password}
        url = f"{self.api_url}/login"
        
        logger.info(f"Login attempt to: {url}")
        
        async with session.post(url, data=data) as resp:
            if resp.status == 200:
                self._cookies = resp.cookies
                logger.info("✅ Logged in to 3x-ui")
                return True
            logger.error(f"❌ Login failed: {resp.status}")
            text = await resp.text()
            logger.error(f"Response: {text}")
            return False

    async def _request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Выполнить запрос к API"""
        # Принудительно авторизуемся перед каждым запросом
        if not self._cookies:
            await self._login()
        
        session = await self._get_session()
        
        headers = {}
        if self._cookies:
            headers["Cookie"] = self._cookies.output(header='')
        
        url = f"{self.api_url}{endpoint}"
        logger.info(f"📡 Request: {method} {url}")
        if data:
            logger.debug(f"Request data: {json.dumps(data, ensure_ascii=False)[:500]}")
        
        async with session.request(method, url, json=data, headers=headers) as resp:
            logger.info(f"Response status: {resp.status}")
            
            if resp.status == 401:
                logger.warning("Session expired, re-logging...")
                await self._login()
                if self._cookies:
                    headers["Cookie"] = self._cookies.output(header='')
                async with session.request(method, url, json=data, headers=headers) as resp2:
                    if resp2.status == 200:
                        return await resp2.json()
                    return None
            elif resp.status == 200:
                return await resp.json()
            else:
                text = await resp.text()
                logger.error(f"❌ Request failed: {resp.status}, response: {text[:200]}")
                return None

    async def add_client(self, days: int = 30, email: str = None) -> Optional[str]:
        """Создать нового клиента на сервере"""
        logger.info(f"📝 add_client called: days={days}, email={email}")
        
        # Создаём нового клиента
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
        
        logger.info(f"Sending add_client request for email: {email}")
        logger.debug(f"Payload: {json.dumps(payload, ensure_ascii=False)}")
        
        result = await self._request('POST', '/panel/api/inbounds/addClient', payload)
        
        if result and result.get('success'):
            logger.info(f"✅ Client created: {client_uuid} (email: {email})")
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
        """Получить информацию о клиенте по UUID"""
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
        server_port: int,
        public_key: str,
        short_id: str,
        plan_name: str,
        sni: str = "www.cloudflare.com",
        fingerprint: str = "chrome"
    ) -> str:
        """Сгенерировать vless:// ссылку для одного сервера"""
        name = urllib.parse.quote(plan_name)
        
        return (
            f"vless://{client_uuid}@{server_host}:{server_port}"
            f"?type=tcp&security=reality"
            f"&pbk={public_key}&fp={fingerprint}"
            f"&sni={sni}&sid={short_id}"
            f"#{name}"
        )

    async def get_all_server_configs(
        self, 
        client_uuid: str, 
        plan_name: str,
        servers: List[Dict] = None
    ) -> List[str]:
        """Сгенерировать ссылки для всех серверов"""
        from config import SERVERS, VPN_SERVER_IP
        
        if servers is None:
            servers = SERVERS
        
        configs = []
        for server in servers:
            display_name = f"{plan_name} - {server['name']}"
            config = await self.get_client_config(
                client_uuid=client_uuid,
                server_host=VPN_SERVER_IP,
                server_port=server['port'],
                public_key=server['public_key'],
                short_id=server['short_id'],
                plan_name=display_name,
                sni=server.get('sni', 'www.cloudflare.com'),
                fingerprint=server.get('fingerprint', 'chrome')
            )
            configs.append(config)
        
        return configs

    async def close(self):
        if self._session:
            await self._session.close()
            logger.info("Session closed")
