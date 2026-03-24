from aiogram import Router, types
from aiogram.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import PROVIDER_TOKEN, MOCK_MODE
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
        
        from config import XUI_HOST, XUI_USERNAME, XUI_PASSWORD, VPN_SERVER_IP
        
        # Создаем клиента в панели
        xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
        
        # Название сервера
        server_name = "Frankfurt"
        
        if MOCK_MODE:
            # Тестовый режим
            client_id = f"mock_{user_id}_{datetime.datetime.now().timestamp()}"
            plan_display_name = f"MILF VPN - {server_name} ({plan.name})"
            sub_link = f"http://87.242.86.245:49828/bJGC3webPGJwCrGw5e/sub/{client_id}"
        else:
            # Добавляем клиента во все инбаунды
            client_id = await xui.add_client_to_all_inbounds(plan.duration_days, email=f"tg_{user_id}")
            if not client_id:
                await message.answer("❌ Ошибка создания подписки. Попробуйте позже.")
                await xui.close()
                return
            
            # Генерируем ссылку-подписку
            sub_link = f"http://87.242.86.245:49828/bJGC3webPGJwCrGw5e/sub/{client_id}"
        
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
        
        # Клавиатура с кнопкой открыть ссылку
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Добавить в V2RayNG", url=sub_link)],
            [InlineKeyboardButton(text="📋 Копировать ссылку", callback_data=f"copy_sub_{client_id}")],
            [InlineKeyboardButton(text="◀ Главное меню", callback_data="main_menu")]
        ])
        
        end_date_str = end_date.strftime('%d.%m.%Y')
        end_time_str = end_date.strftime('%H:%M')
        
        await message.answer(
            f"✅ *Подписка {plan.name} активирована!*\n\n"
            f"📅 *Действует до:* {end_date_str} в {end_time_str} МСК\n\n"
            f"🔗 *Ваша ссылка-подписка:*\n"
            f"`{sub_link}`\n\n"
            f"📱 *Как добавить в V2RayNG:*\n"
            f"1️⃣ Скачайте V2RayNG (Android) или Streisand (iOS)\n"
            f"2️⃣ Нажмите + → Add Subscription\n"
            f"3️⃣ Вставьте ссылку\n"
            f"4️⃣ Нажмите обновить\n\n"
            f"✨ *Доступные серверы:*\n"
            f"🇩🇪 Германия | 🇮🇳 Индия | 🇷🇺 Россия СПБ | 🇮🇹 Италия | 🇹🇷 Турция\n\n"
            f"📖 *Инструкция:* /instructions",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


@router.callback_query(lambda c: c.data.startswith("copy_sub_"))
async def copy_sub_link(callback: types.CallbackQuery):
    """Обработка кнопки копирования ссылки-подписки"""
    client_id = callback.data.split("_")[2]
    sub_link = f"http://87.242.86.245:49828/bJGC3webPGJwCrGw5e/sub/{client_id}"
    
    await callback.answer()
    await callback.message.answer(
        f"🔗 *Ваша ссылка-подписка:*\n`{sub_link}`\n\n"
        f"Скопируйте её и вставьте в V2RayNG → Add Subscription.\n\n"
        f"✨ После добавления у вас появятся все серверы:\n"
        f"🇩🇪 Германия | 🇮🇳 Индия | 🇷🇺 Россия СПБ | 🇮🇹 Италия | 🇹🇷 Турция",
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data.startswith("copy_link_"))
async def copy_link_callback(callback: types.CallbackQuery):
    """Обработка кнопки копирования ссылки (старый формат, для совместимости)"""
    client_id = callback.data.split("_")[2]
    
    async with AsyncSessionLocal() as session:
        from database.models import Subscription, Plan
        from sqlalchemy import select
        
        result = await session.execute(
            select(Subscription, Plan)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(Subscription.client_id == client_id)
        )
        sub_plan = result.first()
        
        if sub_plan:
            sub, plan = sub_plan
            from config import VPN_SERVER_IP
            
            server_name = "Frankfurt"
            plan_display_name = f"MILF VPN - {server_name} ({plan.name})"
            
            sub_link = f"http://87.242.86.245:49828/bJGC3webPGJwCrGw5e/sub/{client_id}"
            
            await callback.answer()
            await callback.message.answer(
                f"🔗 *Ваша ссылка-подписка ({plan_display_name}):*\n\n"
                f"`{sub_link}`\n\n"
                f"📅 *Действует до:* {sub.end_date.strftime('%d.%m.%Y')}\n\n"
                f"Скопируйте её и вставьте в V2RayNG → Add Subscription.",
                parse_mode="Markdown"
            )
        else:
            # Если не нашли в платных, ищем в пробных
            from database.models import Subscription
            sub = await session.execute(
                select(Subscription).where(
                    Subscription.client_id == client_id,
                    Subscription.is_active == True
                )
            )
            sub = sub.scalar_one_or_none()
            
            if sub:
                from config import VPN_SERVER_IP, VPN_REALITY_PUBLIC_KEY, VPN_REALITY_SHORT_ID
                
                server_name = "Frankfurt"
                plan_display_name = "MILF VPN - Frankfurt (Trial)"
                
                sub_link = f"http://87.242.86.245:49828/bJGC3webPGJwCrGw5e/sub/{client_id}"
                
                await callback.answer()
                await callback.message.answer(
                    f"🔗 *Ваша ссылка-подписка ({plan_display_name}):*\n\n"
                    f"`{sub_link}`\n\n"
                    f"📅 *Действует до:* {sub.end_date.strftime('%d.%m.%Y')}\n\n"
                    f"Скопируйте её и вставьте в V2RayNG → Add Subscription.",
                    parse_mode="Markdown"
                )
            else:
                await callback.answer("❌ Подписка не найдена", show_alert=True)
