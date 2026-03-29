from aiogram import Router, types
from aiogram.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import (
    PROVIDER_TOKEN, MOCK_MODE, SUBSCRIPTION_URL
)
from database.session import AsyncSessionLocal
from database.crud import get_plan, get_least_loaded_server, add_subscription, add_transaction, get_user, update_user_marzban_username
from marzban_api import MarzbanAPI
import datetime
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(lambda m: m.successful_payment)
async def successful_payment(message: types.Message):
    """Обработка успешного платежа"""
    payment = message.successful_payment
    payload = payment.invoice_payload
    
    try:
        # Формат payload: "plan_{plan_id}_{user_id}"
        _, plan_id_str, user_id_str = payload.split('_')
        plan_id = int(plan_id_str)
        user_id = int(user_id_str)
    except Exception as e:
        logger.error(f"Error parsing payload: {e}")
        await message.answer("❌ Ошибка обработки платежа. Обратитесь к администратору.")
        return

    async with AsyncSessionLocal() as session:
        # Получаем тариф
        plan = await get_plan(session, plan_id)
        if not plan:
            await message.answer("❌ Тариф не найден.")
            return
        
        # Получаем пользователя
        user = await get_user(session, user_id)
        if not user:
            await message.answer("❌ Пользователь не найден.")
            return
        
        # Создаём клиента в Marzban
        marzban = MarzbanAPI()
        marzban_username = f"tg_{user_id}_{int(datetime.datetime.now().timestamp())}"
        
        if MOCK_MODE:
            client_id = f"mock_{marzban_username}"
            subscription_url = f"https://vpn.olin.mooo.com/sub/{marzban_username}"
        else:
            try:
                await marzban.create_user(
                    username=marzban_username,
                    expire_days=plan.duration_days,
                    data_limit_gb=0
                )
                subscription_url = await marzban.get_subscription_link(marzban_username)
                if not subscription_url:
                    subscription_url = f"https://vpn.olin.mooo.com/sub/{marzban_username}"
                client_id = marzban_username
                
                # Сохраняем marzban_username в БД
                await update_user_marzban_username(session, user_id, marzban_username)
                
                logger.info(f"Marzban user created: {marzban_username} for user {user_id}")
                
            except Exception as e:
                logger.error(f"Marzban API error: {e}")
                await message.answer("❌ Ошибка создания подписки. Попробуйте позже.")
                return
        
        # Сохраняем подписку в БД
        end_date = datetime.datetime.now() + datetime.timedelta(days=plan.duration_days)
        server = await get_least_loaded_server(session)
        await add_subscription(
            session, 
            user_id, 
            plan_id, 
            client_id, 
            server.id if server else 1, 
            end_date
        )
        
        # Сохраняем транзакцию
        await add_transaction(
            session, 
            user_id, 
            payment.total_amount, 
            payment.currency, 
            'stars', 
            str(payment)
        )
        
        await session.commit()
        
        # Клавиатура с кнопками
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Добавить подписку", url=subscription_url)],
            [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data=f"copy_link_{client_id}")],
            [InlineKeyboardButton(text="◀ Главное меню", callback_data="main_menu")]
        ])
        
        end_date_str = end_date.strftime('%d.%m.%Y')
        
        await message.answer(
            f"✅ *Подписка {plan.name} активирована!*\n\n"
            f"📅 *Действует до:* {end_date_str}\n\n"
            f"🔗 *Ваша ссылка-подписка:*\n"
            f"`{subscription_url}`\n\n"
            f"📱 *Как подключиться:*\n"
            f"1️⃣ Скопируйте ссылку\n"
            f"2️⃣ Откройте V2RayNG → + → Add Subscription\n"
            f"3️⃣ Вставьте ссылку\n"
            f"4️⃣ Нажмите обновить\n"
            f"5️⃣ Нажмите ▶️ для подключения\n\n"
            f"⚡ *Совет:* Выберите сервер с наименьшим пингом",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


@router.callback_query(lambda c: c.data.startswith("copy_link_"))
async def copy_link_callback(callback: types.CallbackQuery):
    """Обработка кнопки копирования ссылки"""
    client_id = callback.data.split("_")[2]
    
    async with AsyncSessionLocal() as session:
        from database.models import Subscription
        from sqlalchemy import select
        
        # Ищем подписку
        result = await session.execute(
            select(Subscription).where(Subscription.client_id == client_id)
        )
        sub = result.scalar_one_or_none()
        
        if not sub:
            await callback.answer("Подписка не найдена", show_alert=True)
            return
        
        # Формируем ссылку
        subscription_url = f"https://vpn.olin.mooo.com/sub/{client_id}"
        
        await callback.answer()
        await callback.message.answer(
            f"🔗 *Ваша ссылка-подписка:*\n`{subscription_url}`\n\n"
            f"Скопируйте её и вставьте в V2RayNG → Add Subscription.",
            parse_mode="Markdown"
        )
