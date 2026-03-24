from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from config import MOCK_MODE, XUI_HOST, XUI_USERNAME, XUI_PASSWORD, VPN_SERVER_IP
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
                f"🌐 IP сервера: {VPN_SERVER_IP}"
            )
        else:
            await message.answer(
                "❌ Не удалось подключиться к панели.\n\n"
                "Проверьте:\n"
                "1. XUI_HOST, XUI_USERNAME, XUI_PASSWORD в .env\n"
                "2. Что порт 49828 открыт в группе безопасности\n"
                "3. Что панель запущена на сервере"
            )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        await xui.close()


@router.callback_query(lambda c: c.data.startswith("copy_vpn_"))
async def copy_vpn_link(callback: types.CallbackQuery):
    """Скопировать VPN ссылку"""
    client_id = callback.data.split("_")[2]

    if MOCK_MODE:
        config_link = f"vless://mock@{VPN_SERVER_IP}:443?type=tcp&security=reality#Test_VPN"
    else:
        xui = get_xui_client()
        config_link = await xui.get_client_config(client_id, VPN_SERVER_IP, "VPN")
        await xui.close()

    await callback.answer()
    await callback.message.answer(
        f"🔗 *Ваша ссылка:*\n`{config_link}`\n\n"
        f"Скопируйте её и вставьте в V2RayNG.",
        parse_mode="Markdown"
    )
