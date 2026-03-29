from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from config import MOCK_MODE, MARZBAN_URL, MARZBAN_USERNAME, MARZBAN_PASSWORD, SUBSCRIPTION_URL
from marzban_api import MarzbanAPI
import aiohttp

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("test_vpn"))
async def test_vpn_connection(message: types.Message):
    """Тестовая команда для проверки подключения к Marzban API"""
    if MOCK_MODE:
        await message.answer("⚠️ Режим MOCK_MODE включен. Установите MOCK_MODE=False в .env")
        return

    await message.answer("🔄 Проверяю подключение к Marzban API...")

    try:
        marzban = MarzbanAPI()
        # Пробуем получить список пользователей (проверка подключения)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MARZBAN_URL}/api/users", auth=marzban.auth) as resp:
                if resp.status == 200:
                    await message.answer(
                        f"✅ *Подключение к Marzban API успешно!*\n\n"
                        f"📡 API URL: {MARZBAN_URL}\n"
                        f"👤 Логин: {MARZBAN_USERNAME}\n\n"
                        f"🌍 *Доступные серверы настраиваются в панели Marzban*\n"
                        f"🔗 Панель управления: https://vpn.olin.mooo.com/dashboard/\n\n"
                        f"📋 *Как добавить подписку:*\n"
                        f"1️⃣ Используйте команду /buy в боте\n"
                        f"2️⃣ После оплаты вы получите ссылку-подписку\n"
                        f"3️⃣ Вставьте её в V2RayNG → Add Subscription",
                        parse_mode="Markdown"
                    )
                else:
                    await message.answer(f"❌ Ошибка API: статус {resp.status}\n\nПроверьте настройки MARZBAN_URL, MARZBAN_USERNAME, MARZBAN_PASSWORD в .env")
    except Exception as e:
        await message.answer(f"❌ Ошибка подключения к Marzban: {e}")


@router.message(Command("vpn_servers"))
async def list_vpn_servers(message: types.Message):
    """Показать список доступных VPN-серверов (из панели Marzban)"""
    await message.answer(
        "🌍 *Доступные серверы MILF VPN:*\n\n"
        "Все серверы настраиваются в панели Marzban.\n"
        "После добавления подписки вы получите ссылку,\n"
        "которая автоматически включает все серверы.\n\n"
        "🔗 *Панель управления:* https://vpn.olin.mooo.com/dashboard/\n\n"
        "📋 *Инструкция:*\n"
        "1️⃣ Оплатите подписку через бота\n"
        "2️⃣ Получите ссылку-подписку\n"
        "3️⃣ Добавьте её в V2RayNG (Android) или Streisand (iOS)\n"
        "4️⃣ Нажмите ▶️ для подключения",
        parse_mode="Markdown"
    )


@router.message(Command("servers_info"))
async def servers_info(message: types.Message):
    """Альтернативная команда для списка серверов (без конфликта)"""
    await message.answer(
        "🌍 *Серверы MILF VPN:*\n\n"
        "Серверы настраиваются в панели Marzban.\n"
        "Вы можете добавить несколько серверов в панели,\n"
        "и все они будут доступны по одной ссылке-подписке.\n\n"
        f"🔗 *Ваша подписка:* `{SUBSCRIPTION_URL}`\n\n"
        "💡 *Совет:* Используйте команду /buy для оформления подписки",
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data.startswith("copy_vpn_"))
async def copy_vpn_link(callback: types.CallbackQuery):
    """Скопировать VPN ссылку"""
    parts = callback.data.split("_")
    client_id = parts[2] if len(parts) > 2 else None
    
    if not client_id:
        await callback.answer("Ошибка: идентификатор не найден", show_alert=True)
        return
    
    subscription_url = f"https://vpn.olin.mooo.com/sub/{client_id}"
    
    await callback.answer()
    await callback.message.answer(
        f"🔗 *Ваша ссылка-подписка:*\n`{subscription_url}`\n\n"
        f"📱 *Как добавить в V2RayNG:*\n"
        f"1️⃣ Нажмите + → Add Subscription\n"
        f"2️⃣ Вставьте ссылку\n"
        f"3️⃣ Нажмите обновить\n"
        f"4️⃣ Нажмите ▶️ для подключения\n\n"
        f"💡 *Совет:* После добавления подписки вам будут доступны все серверы",
        parse_mode="Markdown"
    )
