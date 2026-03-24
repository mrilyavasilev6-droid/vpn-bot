from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.models import User, Trial, Subscription
from vpn.xui import XUIClient
from config import XUI_HOST, XUI_USERNAME, XUI_PASSWORD, MOCK_MODE, VPN_SERVER_IP, VPN_REALITY_PUBLIC_KEY, VPN_REALITY_SHORT_ID
import logging

router = Router()


@router.callback_query(lambda c: c.data == "trial_start")
async def trial_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    async with AsyncSessionLocal() as session:
        # Проверяем, был ли уже пробный период
        user = await session.get(User, user_id)
        
        # Проверяем активную триальную подписку
        active_trial = await session.execute(
            select(Trial).where(
                Trial.user_id == user_id,
                Trial.is_active == True,
                Trial.end_date > datetime.now()
            )
        )
        active_trial = active_trial.scalar_one_or_none()
        
        # Проверяем, есть ли уже активная платная подписка
        active_sub = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
                Subscription.end_date > datetime.now()
            )
        )
        active_sub = active_sub.scalar_one_or_none()
        
        if active_sub:
            await callback.message.answer("❌ У вас уже есть активная платная подписка!")
            await callback.answer()
            return
        
        if user and user.trial_used and not active_trial:
            await callback.message.answer("❌ Вы уже использовали пробный период. Оформите платную подписку.")
            await callback.answer()
            return
        
        if active_trial:
            # Уже есть активный пробный период
            await callback.message.answer(
                f"✅ У вас уже активен пробный период!\n\n"
                f"📅 Действует до: {active_trial.end_date.strftime('%d.%m.%Y')}\n\n"
                f"🔑 Нажмите «Получить ключ» в инструкции."
            )
            await callback.answer()
            return
        
        # Создаём нового клиента в панели
        trial_days = 3
        trial_end = datetime.now() + timedelta(days=trial_days)
        
        if MOCK_MODE:
            client_id = f"mock_trial_{user_id}"
        else:
            xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
            client_id = await xui.add_client(trial_days, email=f"trial_{user_id}")
            await xui.close()
            
            if not client_id:
                await callback.message.answer("❌ Ошибка при создании пробной подписки. Попробуйте позже.")
                await callback.answer()
                return
        
        # Сохраняем в БД
        trial = Trial(user_id=user_id, end_date=trial_end, is_active=True)
        session.add(trial)
        
        # Также создаём запись в подписках для отображения в профиле
        subscription = Subscription(
            user_id=user_id,
            plan_id=None,  # пробный период без плана
            client_id=client_id,
            server_id=1,
            start_date=datetime.now(),
            end_date=trial_end,
            is_active=True
        )
        session.add(subscription)
        
        if user:
            user.trial_used = True
            user.trial_end_date = trial_end
        else:
            # Создаём пользователя
            from database.crud import create_user
            user = await create_user(session, user_id, callback.from_user.username)
            user.trial_used = True
            user.trial_end_date = trial_end
        
        await session.commit()
        
        # Генерируем ссылку
        config_link = await generate_trial_link(client_id)
        
        # Показываем инструкцию
        await instructions_step(callback.message, client_id, config_link)
        
    await callback.answer()


async def generate_trial_link(client_id: str) -> str:
    """Сгенерировать vless ссылку для пробного периода"""
    return (
        f"vless://{client_id}@{VPN_SERVER_IP}:443"
        f"?type=tcp&security=reality"
        f"&pbk={VPN_REALITY_PUBLIC_KEY}&fp=chrome"
        f"&sni=www.cloudflare.com&sid={VPN_REALITY_SHORT_ID}"
        f"#Trial"
    )


async def instructions_step(message: types.Message, client_id: str, config_link: str = None):
    """Показать выбор платформы для инструкции"""
    if not config_link:
        # Если ссылки нет, получаем из БД
        async with AsyncSessionLocal() as session:
            sub = await session.execute(
                select(Subscription).where(
                    Subscription.client_id == client_id,
                    Subscription.is_active == True
                )
            )
            sub = sub.scalar_one_or_none()
            if sub:
                config_link = await generate_trial_link(client_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 iPhone", callback_data=f"inst_ios_{client_id}")],
        [InlineKeyboardButton(text="🤖 Android", callback_data=f"inst_android_{client_id}")],
        [InlineKeyboardButton(text="🍎 Mac", callback_data=f"inst_mac_{client_id}")],
        [InlineKeyboardButton(text="🪟 Windows", callback_data=f"inst_windows_{client_id}")],
        [InlineKeyboardButton(text="🔑 Получить ключ", callback_data=f"get_trial_key_{client_id}")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")]
    ])
    
    await message.answer(
        f"✅ *Пробный период 3 дня активирован!*\n\n"
        f"1️⃣ Выберите ваше устройство, чтобы скачать приложение\n"
        f"2️⃣ Нажмите «Получить ключ» для подключения\n\n"
        f"🔑 *Ваш ключ:*\n`{config_link}`",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data.startswith("get_trial_key_"))
async def get_trial_key(callback: types.CallbackQuery):
    """Получить ключ для пробного периода"""
    client_id = callback.data.split("_")[3]
    
    config_link = await generate_trial_link(client_id)
    
    await callback.message.answer(
        f"🔑 *Ваш ключ подключения:*\n\n"
        f"`{config_link}`\n\n"
        f"📱 *Как подключиться:*\n"
        f"1. Скопируйте ссылку\n"
        f"2. Откройте приложение V2RayNG / Streisand\n"
        f"3. Нажмите + → Import from clipboard\n"
        f"4. Нажмите ▶️ для подключения",
        parse_mode="Markdown"
    )
    await callback.answer()
