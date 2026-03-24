import urllib.parse
from typing import Optional
from dataclasses import dataclass
import os


@dataclass
class VPNConfig:
    """Конфигурация VPN-сервера"""
    server_ip: str
    public_key: str
    short_id: str
    sni: str = "www.cloudflare.com"
    port: int = 443
    
    @classmethod
    def from_env(cls):
        """Загрузить конфигурацию из переменных окружения"""
        return cls(
            server_ip=os.getenv('VPN_SERVER_IP', ''),
            public_key=os.getenv('VPN_REALITY_PUBLIC_KEY', ''),
            short_id=os.getenv('VPN_REALITY_SHORT_ID', ''),
            sni=os.getenv('VPN_REALITY_SNI', 'www.cloudflare.com')
        )


def generate_vless_link(client_uuid: str, config: VPNConfig, name: str = None) -> str:
    """
    Сгенерировать vless:// ссылку для подключения
    
    Args:
        client_uuid: UUID клиента
        config: конфигурация сервера
        name: имя подключения (для отображения)
    
    Returns:
        vless:// ссылка
    """
    # Базовый URL
    base = f"vless://{client_uuid}@{config.server_ip}:{config.port}"
    
    # Параметры
    params = {
        "type": "tcp",
        "security": "reality",
        "pbk": config.public_key,
        "fp": "chrome",
        "sni": config.sni,
        "sid": config.short_id
    }
    
    # Собираем параметры в строку
    param_str = "&".join([f"{k}={v}" for k, v in params.items()])
    
    # Добавляем название (если есть)
    if name:
        encoded_name = urllib.parse.quote(name)
        return f"{base}?{param_str}#{encoded_name}"
    
    return f"{base}?{param_str}"


def get_subscription_link(client_uuid: str, panel_url: str, username: str, password: str) -> str:
    """
    Сгенерировать ссылку на подписку (для клиентов)
    
    Args:
        client_uuid: UUID клиента
        panel_url: URL панели управления
        username: логин панели
        password: пароль панели
    
    Returns:
        ссылка на подписку
    """
    # В 3x-ui подписка доступна по адресу /panel/api/inbounds/getClientTraffic?id={uuid}
    # Но для клиентов обычно используется другой формат
    # Это пример, уточните формат в вашей версии 3x-ui
    return f"{panel_url}/subscribe/{client_uuid}"
