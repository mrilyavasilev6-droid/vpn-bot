import json
import time
import uuid
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import aiohttp
from loguru import logger


class XUIClient:
    """Клиент для работы с 3x-ui API"""

    def __init__(self, host: str, username: str, password: str, session: aiohttp.ClientSession = None):
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self._session = session
        self._cookies = None
        self._inbound_id = 1  # ID вашего инбаунда, проверьте в панели

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _login(self) -> bool:
        """Авторизация в панели"""
        session = await self._get_session()
        
        # Сначала получаем login page для cookies
        async with session.get(f"{self.host}/login") as resp:
            pass
        
        # Отправляем данные авторизации
        data = {
            "username": self.username,
            "password": self.password
        }
        
        async with session.post(f"{self.host}/login", data=data) as resp:
            if resp.status == 200:
                logger.info("Successfully logged in to 3x-ui")
                return True
            else:
                logger.error(f"Failed to login: {resp.status}")
                return False

    async def _request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Выполнить запрос к API"""
        session = await self._get_session()
        
        # Пробуем выполнить запрос
        async with session.request(method, f"{self.host}{endpoint}", json=data) as resp:
            if resp.status == 401:
                # Перелогиниваемся
                await self._login()
                async with session.request(method, f"{self.host}{endpoint}", json=data) as resp2:
                    if resp2.status == 200:
                        return await resp2.json()
                    return None
            elif resp.status == 200:
                return await resp.json()
            else:
                logger.error(f"Request failed: {resp.status}")
                return None

    async def add_client(self, days: int = 30) -> Optional[str]:
        """
        Создать нового клиента на сервере
        
        Args:
            days: срок действия подписки в днях
            
        Returns:
            UUID клиента или None в случае ошибки
        """
        client_uuid = str(uuid.uuid4())
        expire_timestamp = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
        
        payload = {
            "id": self._inbound_id,
            "settings": json.dumps({
                "clients": [{
                    "id": client_uuid,
                    "email": f"user_{client_uuid[:8]}",
                    "expireTime": expire_timestamp,
                    "enable": True,
                    "flow": "xtls-rprx-vision",
                    "limitIp": 1,
                    "totalGB": 0
                }]
            })
        }
        
        result = await self._request('POST', '/panel/api/inbounds/addClient', payload)
        
        if result and result.get('success'):
            logger.info(f"Client created: {client_uuid}")
            return client_uuid
        
        logger.error(f"Failed to create client: {result}")
        return None

    async def get_client(self, client_uuid: str) -> Optional[Dict]:
        """Получить информацию о клиенте по UUID"""
        result = await self._request('GET', f'/panel/api/inbounds/getClientTraffic?id={client_uuid}')
        
        if result and result.get('success') and result.get('obj'):
            return result['obj']
        return None

    async def delete_client(self, client_uuid: str) -> bool:
        """Удалить клиента"""
        payload = {
            "id": self._inbound_id,
            "clientId": client_uuid
        }
        
        result = await self._request('POST', '/panel/api/inbounds/delClient', payload)
        
        if result and result.get('success'):
            logger.info(f"Client deleted: {client_uuid}")
            return True
        
        logger.error(f"Failed to delete client: {result}")
        return False

    async def enable_client(self, client_uuid: str, enable: bool = True) -> bool:
        """Включить/отключить клиента"""
        payload = {
            "id": self._inbound_id,
            "clientId": client_uuid,
            "enable": enable
        }
        
        result = await self._request('POST', '/panel/api/inbounds/clientStatus', payload)
        
        if result and result.get('success'):
            logger.info(f"Client {client_uuid} enabled: {enable}")
            return True
        
        logger.error(f"Failed to change client status: {result}")
        return False

    async def get_usage(self, client_uuid: str) -> Optional[int]:
        """Получить использованный трафик клиента в байтах"""
        client = await self.get_client(client_uuid)
        if client:
            return client.get('up', 0) + client.get('down', 0)
        return None

    async def close(self):
        """Закрыть сессию"""
        if self._session:
            await self._session.close()
