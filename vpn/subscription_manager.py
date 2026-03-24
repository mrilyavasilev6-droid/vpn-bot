from datetime import datetime, timedelta
from typing import Optional, Dict
from loguru import logger

from .xui_client import XUIClient
from .config_generator import generate_vless_link, VPNConfig


class SubscriptionManager:
    """Менеджер VPN-подписок"""
    
    def __init__(self, xui_client: XUIClient, vpn_config: VPNConfig):
        self.xui = xui_client
        self.vpn_config = vpn_config
    
    async def create_subscription(self, user_id: int, days: int = 30) -> Optional[Dict]:
        """
        Создать новую подписку для пользователя
        
        Returns:
            Словарь с данными подписки
        """
        try:
            # Создаем клиента на сервере
            client_uuid = await self.xui.add_client(days)
            
            if not client_uuid:
                logger.error(f"Failed to create client for user {user_id}")
                return None
            
            # Генерируем vless ссылку
            vless_link = generate_vless_link(
                client_uuid=client_uuid,
                config=self.vpn_config,
                name=f"User_{user_id}"
            )
            
            # Рассчитываем дату окончания
            expires_at = datetime.now() + timedelta(days=days)
            
            return {
                'user_id': user_id,
                'client_uuid': client_uuid,
                'vless_link': vless_link,
                'created_at': datetime.now(),
                'expires_at': expires_at,
                'active': True
            }
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return None
    
    async def renew_subscription(self, client_uuid: str, days: int = 30) -> bool:
        """
        Продлить подписку
        
        В 3x-ui нет прямого API для продления, нужно:
        1. Получить клиента
        2. Обновить expireTime через API
        """
        try:
            # Получаем клиента
            client = await self.xui.get_client(client_uuid)
            if not client:
                logger.error(f"Client {client_uuid} not found")
                return False
            
            # Обновляем expireTime (через API панели)
            # Здесь нужно реализовать обновление через редактирование клиента
            # В 3x-ui это POST /panel/api/inbounds/updateClient
            new_expire = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
            
            payload = {
                "id": 1,  # ID инбаунда
                "clientId": client_uuid,
                "expireTime": new_expire
            }
            
            result = await self.xui._request('POST', '/panel/api/inbounds/updateClient', payload)
            
            if result and result.get('success'):
                logger.info(f"Subscription renewed for {client_uuid}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error renewing subscription: {e}")
            return False
    
    async def cancel_subscription(self, client_uuid: str) -> bool:
        """Отменить подписку (удалить клиента)"""
        return await self.xui.delete_client(client_uuid)
    
    async def check_subscription_status(self, client_uuid: str) -> Optional[Dict]:
        """Проверить статус подписки"""
        try:
            client = await self.xui.get_client(client_uuid)
            if not client:
                return None
            
            # Проверяем, не истекла ли подписка
            expire_time = client.get('expiryTime', 0)
            is_expired = expire_time > 0 and expire_time < int(datetime.now().timestamp() * 1000)
            
            return {
                'active': client.get('enable', False) and not is_expired,
                'expired': is_expired,
                'expire_time': datetime.fromtimestamp(expire_time / 1000) if expire_time > 0 else None,
                'usage_up': client.get('up', 0),
                'usage_down': client.get('down', 0),
                'total_usage': client.get('up', 0) + client.get('down', 0)
            }
            
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
            return None
