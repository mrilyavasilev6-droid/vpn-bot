from aiogram import Router, types
from aiogram.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import PROVIDER_TOKEN, MOCK_MODE, SERVERS, VPN_SERVER_IP
from database.session import AsyncSessionLocal
from database.crud import get_plan, get_least_loaded_server, add_subscription, add_transaction, get_user
from vpn.xui import XUIClient
import datetime
import logging

router = Router()


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
        logging.error(f"Error parsing payload: {e}")
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
        
        from config import XUI_HOST, XUI_USERNAME, XUI_PASSWORD
        
        # Создаем клиента в панели
        xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
        
        if MOCK_MODE:
            # Тестовый режим
            client_id = f"mock_{user_id}_{datetime.datetime.now().timestamp()}"
            # Генерируем тестовые ссылки для всех серверов
            all_configs = []
            for s in SERVERS:
                mock_config = f"vless://mock@{VPN_SERVER_IP}:{s['port']}?type=tcp&security=reality#MILF%20VPN%20-%20{s['name']}"
                all_configs.append(mock_config)
        else:
            client_id = await xui.add_client(plan.duration_days, email=f"tg_{user_id}")
            if not client_id:
                await message.answer("❌ Ошибка создания подписки. Попробуйте позже.")
                await xui.close()
                return
            
            # Генерируем ссылки для всех серверов
            plan_display_name = f"MILF VPN - {plan.name}"
            all_configs = await xui.get_all_server_configs(client_id, plan_display_name)
        
        # Сохраняем подписку в БД (используем первый сервер как основной)
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
        
        # Формируем сообщение со всеми серверами
        servers_text = "\n".join([f"• {s['name']}" for s in SERVERS])
        
        # Клавиатура с кнопкой добавить все серверы
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Добавить все серверы", callback_data=f"add_all_{client_id}")],
            [InlineKeyboardButton(text="◀ Главное меню", callback_data="main_menu")]
        ])
        
        await message.answer(
            f"✅ *Подписка {plan.name} активирована!*\n\n"
            f"📅 Действует до: {end_date.strftime('%d.%m.%Y')}\n\n"
            f"🌍 *Доступные серверы:*\n{servers_text}\n\n"
            f"🔗 Нажмите кнопку ниже, чтобы добавить ВСЕ серверы в приложение V2RayNG / Streisand:\n\n"
            f"📱 *Инструкция:*\n"
            f"1️⃣ Нажмите кнопку «Добавить все серверы»\n"
            f"2️⃣ Появятся 5 ссылок — нажмите на каждую\n"
            f"3️⃣ Приложение откроется автоматически\n"
            f"4️⃣ Нажмите ▶️ для подключения",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


@router.callback_query(lambda c: c.data.startswith("add_all_"))
async def add_all_servers(callback: types.CallbackQuery):
    """Отправить все конфигурации для импорта"""
    client_id = callback.data.split("_")[2]
    
    async with AsyncSessionLocal() as session:
        from database.crud import get_user_any_active_subscription
        from database.models import Subscription
        from sqlalchemy import select
        
        # Ищем подписку по client_id
        subscription = await session.execute(
            select(Subscription).where(Subscription.client_id == client_id)
        )
        subscription = subscription.scalar_one_or_none()
        
        if not subscription:
            # Ищем по user_id
            subscription = await get_user_any_active_subscription(session, callback.from_user.id)
        
        if not subscription:
            await callback.answer("❌ Подписка не найдена", show_alert=True)
            return
        
        # Определяем название подписки
        if subscription.plan_id:
            plan = await get_plan(session, subscription.plan_id)
            plan_name = plan.name if plan else "VPN"
        else:
            plan_name = "Trial"
        
        from vpn.xui import XUIClient
        from config import XUI_HOST, XUI_USERNAME, XUI_PASSWORD
        
        xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
        
        plan_display_name = f"MILF VPN - {plan_name}"
        all_configs = await xui.get_all_server_configs(subscription.client_id, plan_display_name)
        
        await xui.close()
        
        # Отправляем все ссылки по одной
        for config in all_configs:
            # Извлекаем название сервера из ссылки
            server_name = config.split('#')[-1].replace('_', ' ')
            await callback.message.answer(
                f"🔗 *{server_name}*\n\n"
                f"`{config}`\n\n"
                f"📱 Нажмите на ссылку или скопируйте её и вставьте в приложение.",
                parse_mode="Markdown"
            )
        
        await callback.answer("✅ Все серверы добавлены!")
        await callback.message.answer(
            "🎉 *Готово!*\n\n"
            "Теперь в приложении V2RayNG / Streisand у вас есть 5 серверов:\n"
            + "\n".join([f"• {s['name']}" for s in SERVERS]) +
            "\n\nВыберите любой и нажмите ▶️ для подключения.",
            parse_mode="Markdown"
        )


@router.callback_query(lambda c: c.data.startswith("copy_link_"))
async def copy_link_callback(callback: types.CallbackQuery):
    """Обработка кнопки копирования ссылки (для обратной совместимости)"""
    client_id = callback.data.split("_")[2]
    
    async with AsyncSessionLocal() as session:
        from database.models import Subscription, Plan
        from sqlalchemy import select
        
        result = await session.execute(
            select(Subscription, Plan)
            .join(Plan, Subscription.plan_id == Plan.id, isouter=True)
            .where(Subscription.client_id == client_id)
        )
        sub_plan = result.first()
        
        if sub_plan:
            sub, plan = sub_plan
            plan_name = plan.name if plan else "VPN"
            
            from vpn.xui import XUIClient
            from config import XUI_HOST, XUI_USERNAME, XUI_PASSWORD
            
            xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
            plan_display_name = f"MILF VPN - {plan_name}"
            all_configs = await xui.get_all_server_configs(client_id, plan_display_name)
            await xui.close()
            
            await callback.answer()
            for config in all_configs:
                server_name = config.split('#')[-1].replace('_', ' ')
                await callback.message.answer(
                    f"🔗 *{server_name}*\n\n"
                    f"`{config}`",
                    parse_mode="Markdown"
                )
        else:
            await callback.answer("❌ Подписка не найдена", show_alert=True)
