from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import time
from sqlalchemy import select, delete
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
        active_paid = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
                Subscription.end_date > datetime.now(),
                Subscription.plan_id != None
            )
        )
        active_paid = active_paid.scalar_one_or_none()
        
        if active_paid:
            await callback.message.answer(
                "❌ У вас уже есть активная *платная* подписка.\n\n"
                "Пробный период доступен только для новых пользователей.",
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        
        # Удаляем старые неактивные пробные периоды
        await session.execute(
            delete(Trial).where(
                Trial.user_id == user_id,
                Trial.is_active == False
            )
        )
        
        # Удаляем старые неактивные подписки (пробные)
        await session.execute(
            delete(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.plan_id == None,
                Subscription.is_active == False
            )
        )
        
        await session.commit()
        
        # Проверяем активный пробный период
        active_trial = await session.execute(
            select(Trial).where(
                Trial.user_id == user_id,
                Trial.is_active == True,
                Trial.end_date > datetime.now()
            )
        )
        active_trial = active_trial.scalar_one_or_none()
        
        if active_trial:
            end_date = active_trial.end_date.strftime('%d.%m.%Y')
            end_time = active_trial.end_date.strftime('%H:%M')
            await callback.message.answer(
                f"✅ *У вас уже активен пробный период!*\n\n"
                f"📅 Действует до: {end_date} в {end_time} МСК\n\n"
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
        
        # Проверяем, использовал ли пользователь пробный период раньше
        if user and user.trial_used:
            await callback.message.answer(
                "❌ Вы уже использовали пробный период.\n\n"
                "💎 Оформите платную подписку в разделе «Выбрать тариф».",
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        
        # Создаём нового клиента в панели
        trial_days = 3
        trial_end = datetime.now() + timedelta(days=trial_days)
        
        logger.info(f"Creating trial client for user {user_id}")
        
        # Используем уникальный email с timestamp
        email = f"trial_{user_id}_{int(time.time())}"
        
        if MOCK_MODE:
            client_id = f"mock_trial_{user_id}"
        else:
            try:
                xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
                client_id = await xui.add_client(trial_days, email=email)
                await xui.close()
                
                if not client_id:
                    logger.error(f"Failed to create client for user {user_id}")
                    await callback.message.answer("❌ Ошибка при создании пробной подписки. Попробуйте позже.")
                    await callback.answer()
                    return
                else:
                    logger.info(f"Client created with UUID: {client_id}, email: {email}")
            except Exception as e:
                logger.error(f"Error creating client: {e}")
                await callback.message.answer("❌ Ошибка подключения к VPN серверу. Попробуйте позже.")
                await callback.answer()
                return
        
        # Сохраняем в таблицу Trial
        trial = Trial(
            user_id=user_id,
            end_date=trial_end,
            is_active=True
        )
        session.add(trial)
        await session.flush()
        
        # Сохраняем в таблицу Subscription
        subscription = Subscription(
            user_id=user_id,
            plan_id=None,
            client_id=client_id,
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
        
        end_date_str = trial_end.strftime('%d.%m.%Y')
        end_time_str = trial_end.strftime('%H:%M')
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions")],
            [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")],
            [InlineKeyboardButton(text="◀ Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.answer(
            f"🎉 *Пробный период 3 дня активирован!*\n\n"
            f"🔑 *Ваш ключ:*\n`{config_link}`\n\n"
            f"📅 *Действует до:* {end_date_str} в {end_time_str} МСК\n\n"
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
