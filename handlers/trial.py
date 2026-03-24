from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.models import User, Trial, Server
from vpn.xui import XUIClient
from config import XUI_HOST, XUI_USERNAME, XUI_PASSWORD, MOCK_MODE
import logging

router = Router()


@router.callback_query(lambda c: c.data == "trial_start")
async def trial_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if user.trial_used:
            await callback.message.answer("❌ Вы уже использовали пробный период.")
            await callback.answer()
            return

        # Создаем клиента в панели
        if MOCK_MODE:
            client_id = f"mock_trial_{user_id}"
        else:
            xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
            client_id = await xui.add_client(3, email=f"trial_{user_id}")
            await xui.close()
            
            if not client_id:
                await callback.message.answer("❌ Ошибка при создании пробной подписки. Попробуйте позже.")
                await callback.answer()
                return

        trial_end = datetime.now() + timedelta(days=3)
        trial = Trial(user_id=user_id, end_date=trial_end, is_active=True)
        session.add(trial)

        user.trial_used = True
        user.trial_end_date = trial_end

        await session.commit()

    # После создания показываем инструкцию
    await instructions_step(callback.message, client_id)
    await callback.answer()


async def instructions_step(message: types.Message, client_id: str):
    """Показать выбор платформы для инструкции"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 iPhone", callback_data=f"inst_ios_{client_id}")],
        [InlineKeyboardButton(text="🤖 Android", callback_data=f"inst_android_{client_id}")],
        [InlineKeyboardButton(text="🍎 Mac", callback_data=f"inst_mac_{client_id}")],
        [InlineKeyboardButton(text="🪟 Windows", callback_data=f"inst_windows_{client_id}")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")]
    ])
    await message.answer(
        "✅ Вам доступен **Пробный период 3 дня**\n\n"
        "1️⃣ Скачайте приложение для подключения к VPN\n"
        "Выберите вашу платформу:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
