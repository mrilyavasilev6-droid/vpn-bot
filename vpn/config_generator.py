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
    base = f"vless://{client_uuid}@{config.server_ip}:{config.port}"
    
    params = {
        "type": "tcp",
        "security": "reality",
        "pbk": config.public_key,
        "fp": "chrome",
        "sni": config.sni,
        "sid": config.short_id
    }
    
    param_str = "&".join([f"{k}={v}" for k, v in params.items()])
    
    if name:
        encoded_name = urllib.parse.quote(name)
        return f"{base}?{param_str}#{encoded_name}"
    
    return f"{base}?{param_str}"


def get_subscription_link(client_uuid: str, panel_url: str, username: str, password: str) -> str:
    """Сгенерировать ссылку на подписку (для клиентов)"""
    return f"{panel_url}/subscribe/{client_uuid}"
