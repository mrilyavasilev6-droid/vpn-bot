from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import time
from sqlalchemy import select, delete
from database.session import AsyncSessionLocal
from database.models import User, Trial, Subscription
from marzban_api import MarzbanAPI
from database.crud import update_user_marzban_username
from config import MOCK_MODE, SUBSCRIPTION_URL
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
        
        # Создаём пробного клиента в Marzban
        trial_days = 3
        trial_end = datetime.now() + timedelta(days=trial_days)
        
        logger.info(f"Creating trial client for user {user_id}")
        
        marzban = MarzbanAPI()
        
        if MOCK_MODE:
            marzban_username = f"mock_trial_{user_id}"
            subscription_url = f"https://vpn.olin.mooo.com/sub/{marzban_username}"
            client_id = marzban_username
        else:
            try:
                marzban_username = f"trial_{user_id}_{int(time.time())}"
                
                await marzban.create_user(
                    username=marzban_username,
                    expire_days=trial_days,
                    data_limit_gb=0
                )
                
                subscription_url = await marzban.get_subscription_link(marzban_username)
                if not subscription_url:
                    subscription_url = f"https://vpn.olin.mooo.com/sub/{marzban_username}"
                client_id = marzban_username
                
                # Сохраняем marzban_username в БД
                await update_user_marzban_username(session, user_id, marzban_username)
                
                logger.info(f"Marzban trial user created: {marzban_username}")
                
            except Exception as e:
                logger.error(f"Error creating trial client in Marzban: {e}")
                await callback.message.answer("❌ Ошибка при создании пробной подписки. Попробуйте позже.")
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
        
        end_date_str = trial_end.strftime('%d.%m.%Y')
        end_time_str = trial_end.strftime('%H:%M')
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions")],
            [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")],
            [InlineKeyboardButton(text="◀ Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.answer(
            f"🎉 *Пробный период {trial_days} дня активирован!*\n\n"
            f"🔗 *Ваша ссылка-подписка:*\n`{subscription_url}`\n\n"
            f"📅 *Действует до:* {end_date_str} в {end_time_str} МСК\n\n"
            f"📱 *Как подключиться:*\n"
            f"1️⃣ Скопируйте ссылку\n"
            f"2️⃣ Откройте V2RayNG → + → Add Subscription\n"
            f"3️⃣ Вставьте ссылку\n"
            f"4️⃣ Нажмите обновить\n"
            f"5️⃣ Нажмите ▶️ для подключения\n\n"
            f"💡 *Совет:* После активации платной подписки вам не нужно менять настройки — всё работает автоматически",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    await callback.answer()
