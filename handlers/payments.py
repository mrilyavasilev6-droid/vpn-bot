from aiogram import Router, types
from aiogram.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import (
    PROVIDER_TOKEN, MOCK_MODE, XUI_HOST, XUI_USERNAME, XUI_PASSWORD,
    VPN_SERVER_IP, SERVERS, SERVER_UUID, SUBSCRIPTION_URL, REALITY_SNI, REALITY_FINGERPRINT
)
from database.session import AsyncSessionLocal
from database.crud import get_plan, get_least_loaded_server, add_subscription, add_transaction, get_user
from vpn.xui import XUIClient
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
        
        # Получаем сервер (если используется несколько)
        server = await get_least_loaded_server(session)
        
        # Создаем клиента в панели
        xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
        
        if MOCK_MODE:
            # Тестовый режим
            client_id = f"mock_{user_id}_{datetime.datetime.now().timestamp()}"
            # Генерируем тестовые ссылки
            links_text = ""
            for s in SERVERS:
                links_text += f"{s['name']}\n`vless://mock@{VPN_SERVER_IP}:{s['port']}?type=tcp&security=reality#Mock_{s['name']}`\n\n"
        else:
            # Создаем клиента в панели
            email = f"tg_{user_id}_{int(datetime.datetime.now().timestamp())}"
            client_id = await xui.add_client(plan.duration_days, email=email)
            
            if not client_id:
                await message.answer("❌ Ошибка создания подписки. Попробуйте позже.")
                await xui.close()
                return
            
            logger.info(f"Client created: {client_id} for user {user_id}")
            
            # Генерируем ссылки для всех серверов
            server_host = VPN_SERVER_IP or "panel.3utilities.com"
            links = await xui.get_all_configs(
                client_uuid=client_id,
                server_host=server_host,
                servers=SERVERS,
                sni=REALITY_SNI,
                fingerprint=REALITY_FINGERPRINT
            )
            
            # Форматируем ссылки для отправки
            links_text = ""
            for i, s in enumerate(SERVERS):
                links_text += f"{s['name']}\n`{links[i]}`\n\n"
        
        # Сохраняем подписку в БД
        end_date = datetime.datetime.now() + datetime.timedelta(days=plan.duration_days)
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
        
        # Если сервер существует, обновляем количество клиентов
        if server and not MOCK_MODE:
            server.current_clients += 1
            await session.commit()
        
        await xui.close()
        
        # Клавиатура с кнопками
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Добавить подписку", url=SUBSCRIPTION_URL)],
            [InlineKeyboardButton(text="📋 Скопировать ссылки", callback_data=f"copy_links_{client_id}")],
            [InlineKeyboardButton(text="◀ Главное меню", callback_data="main_menu")]
        ])
        
        await message.answer(
            f"✅ *Подписка {plan.name} активирована!*\n\n"
            f"📅 *Действует до:* {end_date.strftime('%d.%m.%Y')}\n\n"
            f"🌍 *Ваши серверы:*\n\n{links_text}\n"
            f"🔗 *Или добавьте одну подписку:*\n"
            f"`{SUBSCRIPTION_URL}`\n\n"
            f"📱 *Как подключиться:*\n"
            f"1️⃣ Скопируйте ссылку нужного сервера или добавьте подписку\n"
            f"2️⃣ Откройте V2RayNG → + → Import from clipboard / Add Subscription\n"
            f"3️⃣ Нажмите ▶️ для подключения\n\n"
            f"⚡ *Совет:* Выберите сервер с наименьшим пингом",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


@router.callback_query(lambda c: c.data.startswith("copy_links_"))
async def copy_links_callback(callback: types.CallbackQuery):
    """Обработка кнопки копирования ссылок"""
    client_id = callback.data.split("_")[2]
    
    async with AsyncSessionLocal() as session:
        from database.models import Subscription, Plan
        from sqlalchemy import select
        
        # Ищем подписку
        result = await session.execute(
            select(Subscription, Plan)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(Subscription.client_id == client_id)
        )
        sub_plan = result.first()
        
        if not sub_plan:
            # Пробуем найти без плана (пробный период)
            sub = await session.execute(
                select(Subscription).where(
                    Subscription.client_id == client_id,
                    Subscription.is_active == True
                )
            )
            sub = sub.scalar_one_or_none()
            if sub:
                plan_name = "Пробный период"
            else:
                await callback.answer("Подписка не найдена", show_alert=True)
                return
        else:
            sub, plan = sub_plan
            plan_name = plan.name
        
        # Генерируем ссылки
        xui = XUIClient(None, None, None)
        server_host = VPN_SERVER_IP or "panel.3utilities.com"
        links = await xui.get_all_configs(
            client_uuid=client_id,
            server_host=server_host,
            servers=SERVERS,
            sni=REALITY_SNI,
            fingerprint=REALITY_FINGERPRINT
        )
        
        links_text = ""
        for i, s in enumerate(SERVERS):
            links_text += f"{s['name']}\n`{links[i]}`\n\n"
        
        await callback.answer()
        await callback.message.answer(
            f"🔗 *Ваши ссылки ({plan_name}):*\n\n{links_text}\n"
            f"📅 *Действует до:* {sub.end_date.strftime('%d.%m.%Y')}\n\n"
            f"Скопируйте ссылки и вставьте в V2RayNG.",
            parse_mode="Markdown"
        )
