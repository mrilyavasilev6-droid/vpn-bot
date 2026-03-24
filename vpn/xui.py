import aiohttp
import json
import uuid
import urllib.parse
import os
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
        self._inbound_id = 1  # ID инбаунда по умолчанию
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
        """Создать нового клиента на сервере (только в один инбаунд)"""
        logger.info(f"📝 add_client called: days={days}, email={email}")
        
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
        
        result = await self._request('POST', '/panel/api/inbounds/addClient', payload)
        
        if result and result.get('success'):
            logger.info(f"✅ Client created: {client_uuid} (email: {email})")
            return client_uuid
        
        logger.error(f"❌ Failed to create client: {result}")
        return None

    async def add_client_to_all_inbounds(self, days: int = 30, email: str = None) -> Optional[str]:
        """Создать клиента во всех инбаундах с одним UUID"""
        
        # Создаём один UUID для всех серверов
        client_uuid = str(uuid.uuid4())
        expire_timestamp = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
        
        if not email:
            email = f"user_{client_uuid[:8]}"
        
        # Список всех инбаундов (ID, порт, название)
        # ID инбаундов из вашей панели: 2-Германия, 3-Индия, 4-Россия, 5-Италия, 6-Турция
        inbounds = [
            {"id": 2, "port": 443, "name": "Германия"},
            {"id": 3, "port": 444, "name": "Индия"},
            {"id": 4, "port": 445, "name": "Россия СПБ"},
            {"id": 5, "port": 446, "name": "Италия"},
            {"id": 6, "port": 447, "name": "Турция"},
        ]
        
        success_count = 0
        
        for inbound in inbounds:
            payload = {
                "id": inbound["id"],
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
            
            logger.info(f"Adding client to inbound {inbound['id']} ({inbound['name']})")
            
            result = await self._request('POST', '/panel/api/inbounds/addClient', payload)
            
            if result and result.get('success'):
                success_count += 1
                logger.info(f"✅ Client added to {inbound['name']}")
            else:
                logger.error(f"❌ Failed to add client to {inbound['name']}: {result}")
        
        if success_count > 0:
            logger.info(f"✅ Client created in {success_count}/{len(inbounds)} inbounds")
            return client_uuid
        
        return None

    async def delete_client(self, client_uuid: str) -> bool:
        """Удалить клиента из всех инбаундов"""
        # Список всех инбаундов
        inbounds = [2, 3, 4, 5, 6]
        success_count = 0
        
        for inbound_id in inbounds:
            payload = {"id": inbound_id, "clientId": client_uuid}
            result = await self._request('POST', '/panel/api/inbounds/delClient', payload)
            
            if result and result.get('success'):
                success_count += 1
                logger.info(f"✅ Client deleted from inbound {inbound_id}")
            else:
                logger.error(f"❌ Failed to delete client from inbound {inbound_id}: {result}")
        
        return success_count > 0

    async def get_client(self, client_uuid: str) -> Optional[Dict]:
        """Получить информацию о клиенте по UUID (из первого инбаунда)"""
        result = await self._request('GET', f'/panel/api/inbounds/getClientTraffic?id={client_uuid}')
        
        if result and result.get('success') and result.get('obj'):
            return result['obj']
        return None

    async def get_client_all_inbounds(self, client_uuid: str) -> Optional[Dict]:
        """Получить суммарную информацию о клиенте по всем инбаундам"""
        # Список всех инбаундов
        inbounds = [2, 3, 4, 5, 6]
        total_up = 0
        total_down = 0
        
        for inbound_id in inbounds:
            result = await self._request('GET', f'/panel/api/inbounds/getClientTraffic?id={client_uuid}&inbound={inbound_id}')
            if result and result.get('success') and result.get('obj'):
                total_up += result['obj'].get('up', 0)
                total_down += result['obj'].get('down', 0)
                logger.debug(f"Traffic from inbound {inbound_id}: up={result['obj'].get('up', 0)}, down={result['obj'].get('down', 0)}")
        
        if total_up > 0 or total_down > 0:
            return {
                'up': total_up,
                'down': total_down,
                'total': total_up + total_down
            }
        return None

    async def enable_client(self, client_uuid: str, enable: bool = True) -> bool:
        """Включить/отключить клиента во всех инбаундах"""
        inbounds = [2, 3, 4, 5, 6]
        success_count = 0
        
        for inbound_id in inbounds:
            payload = {"id": inbound_id, "clientId": client_uuid, "enable": enable}
            result = await self._request('POST', '/panel/api/inbounds/clientStatus', payload)
            if result and result.get('success'):
                success_count += 1
        
        return success_count > 0

    async def get_client_config(
        self, 
        client_uuid: str, 
        server_host: str, 
        plan_name: str,
        public_key: str = None,
        short_id: str = None,
        sni: str = None
    ) -> str:
        """Сгенерировать vless:// ссылку для подключения (для одного сервера)"""
        pbk = public_key or os.getenv('VPN_REALITY_PUBLIC_KEY', '')
        sid = short_id or os.getenv('VPN_REALITY_SHORT_ID', '')
        sni_value = sni or os.getenv('VPN_REALITY_SNI', 'www.cloudflare.com')
        
        if not pbk:
            pbk = "NnIZ6QgJpOYfL7K7NuS4lWuDNdhRNOQlshTf6SK4O2Y"
            logger.warning("Using default public key")
        if not sid:
            sid = "9020f7"
            logger.warning("Using default short id")
        
        name = urllib.parse.quote(plan_name)
        
        config = (
            f"vless://{client_uuid}@{server_host}:443"
            f"?type=tcp&security=reality"
            f"&pbk={pbk}&fp=chrome"
            f"&sni={sni_value}&sid={sid}"
            f"#{name}"
        )
        
        logger.info(f"Generated config for {client_uuid}")
        return config

    async def get_subscription_link(self, client_uuid: str) -> str:
        """Сгенерировать ссылку-подписку для V2RayNG"""
        return f"{self.api_url}/sub/{client_uuid}"

    async def close(self):
        if self._session:
            await self._session.close()
            logger.info("Session closed")
