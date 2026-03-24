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
logger = logging.getLogger(__name__)


@router.callback_query(lambda c: c.data == "trial_start")
async def trial_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    logger.info(f"Trial start requested by user {user_id}")
    
    async with AsyncSessionLocal() as session:
        # Проверяем пользователя
        user = await session.get(User, user_id)
        
        # Проверяем активную платную подписку
        active_sub = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
                Subscription.end_date > datetime.now()
            )
        )
        active_sub = active_sub.scalar_one_or_none()
        
        if active_sub:
            logger.info(f"User {user_id} already has active subscription")
            await callback.message.answer("❌ У вас уже есть активная платная подписка!")
            await callback.answer()
            return
        
        # Проверяем активный пробный период в таблице Trial
        active_trial = await session.execute(
            select(Trial).where(
                Trial.user_id == user_id,
                Trial.is_active == True,
                Trial.end_date > datetime.now()
            )
        )
        active_trial = active_trial.scalar_one_or_none()
        
        if active_trial:
            # Если есть активный пробный период, показываем информацию
            end_date = active_trial.end_date.strftime('%d.%m.%Y')
            await callback.message.answer(
                f"✅ *У вас уже активен пробный период!*\n\n"
                f"📅 Действует до: {end_date}\n\n"
                f"🔑 Нажмите «Инструкция» → «Получить ключ».",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions")],
                    [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")],
                    [InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")]
                ]),
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        
        # Проверяем, не использовал ли пользователь пробный период раньше
        if user and user.trial_used:
            logger.info(f"User {user_id} already used trial before")
            await callback.message.answer("❌ Вы уже использовали пробный период. Оформите платную подписку.")
            await callback.answer()
            return
        
        # Создаём нового клиента в панели
        trial_days = 3
        trial_end = datetime.now() + timedelta(days=trial_days)
        
        logger.info(f"Creating trial client for user {user_id}")
        
        if MOCK_MODE:
            client_id = f"mock_trial_{user_id}"
        else:
            xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
            client_id = await xui.add_client(trial_days, email=f"trial_{user_id}")
            await xui.close()
            
            if not client_id:
                logger.error(f"Failed to create client for user {user_id}")
                await callback.message.answer("❌ Ошибка при создании пробной подписки. Попробуйте позже.")
                await callback.answer()
                return
        
        logger.info(f"Client created: {client_id}")
        
        # Сохраняем в таблицу Trial
        trial = Trial(
            user_id=user_id,
            end_date=trial_end,
            is_active=True
        )
        session.add(trial)
        await session.flush()  # Получаем trial.id
        
        # Сохраняем в таблицу Subscription с client_id
        subscription = Subscription(
            user_id=user_id,
            plan_id=None,  # пробный период без плана
            client_id=client_id,  # сохраняем UUID клиента
            server_id=1,
            start_date=datetime.now(),
            end_date=trial_end,
            is_active=True
        )
        session.add(subscription)
        
        # Обновляем пользователя
        if user:
            user.trial_used = True
            user.trial_end_date = trial_end
        else:
            from database.crud import create_user
            user = await create_user(session, user_id, callback.from_user.username)
            user.trial_used = True
            user.trial_end_date = trial_end
        
        await session.commit()
        
        logger.info(f"Trial saved to DB for user {user_id}, expires at {trial_end}, client_id={client_id}")
        
        # Генерируем ссылку
        config_link = (
            f"vless://{client_id}@{VPN_SERVER_IP}:443"
            f"?type=tcp&security=reality"
            f"&pbk={VPN_REALITY_PUBLIC_KEY}&fp=chrome"
            f"&sni=www.cloudflare.com&sid={VPN_REALITY_SHORT_ID}"
            f"#Trial"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions")],
            [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")],
            [InlineKeyboardButton(text="◀ Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.answer(
            f"🎉 *Пробный период 3 дня активирован!*\n\n"
            f"🔑 *Ваш ключ:*\n`{config_link}`\n\n"
            f"📅 Действует до: {trial_end.strftime('%d.%m.%Y')}\n\n"
            f"📱 *Как подключиться:*\n"
            f"1️⃣ Скачайте V2RayNG (Android) или Streisand (iOS)\n"
            f"2️⃣ Нажмите + → Import from clipboard\n"
            f"3️⃣ Вставьте ссылку\n"
            f"4️⃣ Нажмите ▶️ для подключения\n\n"
            f"Инструкцию можно найти в меню «Инструкция»",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    await callback.answer()
