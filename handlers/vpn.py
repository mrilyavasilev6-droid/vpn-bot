from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from config import MOCK_MODE, XUI_HOST, XUI_USERNAME, XUI_PASSWORD, VPN_SERVER_IP, SERVERS, REALITY_SNI, REALITY_FINGERPRINT
from vpn.xui import XUIClient

logger = logging.getLogger(__name__)
router = Router()


def get_xui_client():
    """Получить клиент 3x-ui"""
    if MOCK_MODE:
        return None
    return XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)


@router.message(Command("test_vpn"))
async def test_vpn_connection(message: types.Message):
    """Тестовая команда для проверки подключения к панели"""
    if MOCK_MODE:
        await message.answer("⚠️ Режим MOCK_MODE включен. Установите MOCK_MODE=False в .env")
        return

    await message.answer("🔄 Проверяю подключение к панели 3x-ui...")

    xui = get_xui_client()
    try:
        success = await xui._login()
        if success:
            await message.answer(
                "✅ Подключение к панели 3x-ui успешно!\n\n"
                f"📡 Сервер: {XUI_HOST}\n"
                f"👤 Логин: {XUI_USERNAME}\n"
                f"🌐 IP сервера: {VPN_SERVER_IP}\n\n"
                f"🌍 *Доступные серверы:*\n"
                f"🇩🇪 Германия | 🇮🇳 Индия | 🇷🇺 Россия | 🇮🇹 Италия | 🇹🇷 Турция"
            )
        else:
            await message.answer(
                "❌ Не удалось подключиться к панели.\n\n"
                "Проверьте:\n"
                "1. XUI_HOST, XUI_USERNAME, XUI_PASSWORD в .env\n"
                "2. Что порт 39721 открыт в группе безопасности\n"
                "3. Что панель запущена на сервере"
            )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        await xui.close()


@router.message(Command("vpn_servers"))
async def list_vpn_servers(message: types.Message):
    """Показать список доступных VPN-серверов"""
    servers_text = "🌍 *Доступные серверы MILF VPN:*\n\n"
    for s in SERVERS:
        servers_text += f"{s['name']}\n"
        servers_text += f"   📡 Порт: {s['port']}\n"
        servers_text += f"   🔑 Short ID: {s['short_id'][:8]}...\n\n"
    
    await message.answer(servers_text, parse_mode="Markdown")


@router.message(Command("servers_info"))
async def servers_info(message: types.Message):
    """Альтернативная команда для списка серверов (без конфликта)"""
    servers_text = "🌍 *Серверы MILF VPN:*\n\n"
    for i, s in enumerate(SERVERS, 1):
        servers_text += f"{i}. {s['name']} (порт {s['port']})\n"
    
    await message.answer(servers_text, parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("copy_vpn_"))
async def copy_vpn_link(callback: types.CallbackQuery):
    """Скопировать VPN ссылку (для конкретного сервера)"""
    parts = callback.data.split("_")
    client_id = parts[2]
    server_index = int(parts[3]) if len(parts) > 3 else 0
    
    if MOCK_MODE:
        config_link = f"vless://mock@{VPN_SERVER_IP}:443?type=tcp&security=reality#Test_VPN"
    else:
        if server_index < len(SERVERS):
            server = SERVERS[server_index]
            xui = get_xui_client()
            config_link = await xui.get_client_config(
                client_uuid=client_id,
                server_host=VPN_SERVER_IP,
                port=server['port'],
                public_key=server['public_key'],
                short_id=server['short_id'],
                name=server['name'],
                sni=REALITY_SNI,
                fingerprint=REALITY_FINGERPRINT
            )
            await xui.close()
        else:
            # fallback на первый сервер
            server = SERVERS[0]
            xui = get_xui_client()
            config_link = await xui.get_client_config(
                client_uuid=client_id,
                server_host=VPN_SERVER_IP,
                port=server['port'],
                public_key=server['public_key'],
                short_id=server['short_id'],
                name=server['name'],
                sni=REALITY_SNI,
                fingerprint=REALITY_FINGERPRINT
            )
            await xui.close()
    
    await callback.answer()
    await callback.message.answer(
        f"🔗 *Ваша ссылка:*\n`{config_link}`\n\n"
        f"Скопируйте её и вставьте в V2RayNG.\n\n"
        f"💡 *Совет:* Используйте `/vpn_servers` для просмотра всех доступных серверов.",
        parse_mode="Markdown"
    )
