from abc import ABC, abstractmethod

class VPNClient(ABC):
    """Абстрактный класс для работы с VPN-панелью"""

    @abstractmethod
    async def add_client(self, days: int) -> str:
        """Создаёт клиента на сервере и возвращает его ID"""
        pass

    @abstractmethod
    async def delete_client(self, client_id: str) -> bool:
        """Удаляет клиента с сервера"""
        pass

    @abstractmethod
    async def get_client_config(self, client_id: str) -> str:
        """Возвращает конфигурацию клиента"""
        pass