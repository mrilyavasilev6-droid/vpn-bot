from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.models import User, Trial, Server
from vpn.xui import XUIClient
from config import XUI_HOST, XUI_USERNAME, XUI_PASSWORD
import logging

router = Router()

@router.callback_query(lambda c: c.data == "trial_start")
async def trial_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if user.trial_used:
            await callback.message.answer("Вы уже использовали пробный период.")
            await callback.answer()
            return

        # Проверяем, есть ли свободный сервер
        server = await session.execute(select(Server).where(Server.max_clients > Server.current_clients))
        server = server.scalars().first()
        if not server:
            await callback.message.answer("Нет свободных серверов. Попробуйте позже.")
            return

        xui = XUIClient(server.api_url, server.api_username, server.api_password)
        client_id = await xui.add_client(3)   # создаём клиента на 3 дня
        if not client_id:
            await callback.message.answer("Ошибка при создании пробной подписки.")
            return

        # Обновляем счётчик клиентов на сервере
        server.current_clients += 1

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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="iPhone", callback_data=f"inst_ios_{client_id}")],
        [InlineKeyboardButton(text="Android", callback_data=f"inst_android_{client_id}")],
        [InlineKeyboardButton(text="Mac", callback_data=f"inst_mac_{client_id}")],
        [InlineKeyboardButton(text="Windows", callback_data=f"inst_windows_{client_id}")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")]
    ])
    await message.answer(
        "✅ Вам доступен **Пробный период 3 дня** для одного мобильного устройства и компьютера\n\n"
        "Ниже инструкция как его получить:\n\n"
        "1️⃣ Скачайте бесплатное приложение через которое вы будете подключаться к VPN\n"
        "Выберите вашу платформу:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
