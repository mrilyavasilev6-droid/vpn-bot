from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.crud import get_plan
from database.models import Trial, Subscription
from config import VPN_SERVER_IP, VPN_REALITY_PUBLIC_KEY, VPN_REALITY_SHORT_ID
import logging

router = Router()  # ← ЭТО БЫЛО ПРОПУЩЕНО
logger = logging.getLogger(__name__)


async def get_active_subscription(session, user_id: int):
    """Получить активную подписку (платную или пробную)"""
    now = datetime.now()
    
    # Ищем в Subscription любую активную
    sub = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active == True,
            Subscription.end_date > now
        )
    )
    subscription = sub.scalar_one_or_none()
    
    if subscription:
        logger.info(f"Found subscription for user {user_id}, expires at {subscription.end_date}")
        return subscription
    
    # Если нет подписки, проверяем Trial
    trial = await session.execute(
        select(Trial).where(
            Trial.user_id == user_id,
            Trial.is_active == True,
            Trial.end_date > now
        )
    )
    trial = trial.scalar_one_or_none()
    
    if trial:
        logger.info(f"Found trial for user {user_id}, expires at {trial.end_date}")
        return None
    
    return None


@router.callback_query(lambda c: c.data == "instructions")
async def instructions_start(callback: types.CallbackQuery):
    """Показать общую инструкцию"""
    text = (
        "📖 *Инструкция по установке MILF VPN*\n\n"
        "1️⃣ В Главном меню выберите **Пробный период** или оформите **Подписку**\n\n"
        "2️⃣ После активации выберите вашу платформу:\n"
        "   • iPhone / iPad — Streisand\n"
        "   • Android — V2RayNG\n"
        "   • Mac — V2RayU\n"
        "   • Windows — v2rayN\n\n"
        "3️⃣ Скачайте и установите приложение\n\n"
        "4️⃣ Нажмите **Получить ключ** — ссылка добавится автоматически\n\n"
        "5️⃣ Откройте ссылку — приложение откроется и импортирует конфигурацию\n\n"
        "6️⃣ Нажмите ▶️ в приложении для подключения\n\n"
        "✅ Готово! Интернет защищён."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Выбрать платформу", callback_data="choose_platform")],
        [InlineKeyboardButton(text="🔑 Получить ключ", callback_data="get_key")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(lambda c: c.data == "choose_platform")
async def choose_platform(callback: types.CallbackQuery):
    """Выбор платформы"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 iPhone / iPad", callback_data="inst_ios")],
        [InlineKeyboardButton(text="🤖 Android", callback_data="inst_android")],
        [InlineKeyboardButton(text="🍎 Mac", callback_data="inst_mac")],
        [InlineKeyboardButton(text="🪟 Windows", callback_data="inst_windows")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="instructions")]
    ])
    
    await callback.message.answer(
        "📱 *Выберите вашу платформу:*\n\n"
        "Нажмите на кнопку с вашим устройством, чтобы получить ссылку на приложение и инструкцию.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("inst_"))
async def show_platform_instruction(callback: types.CallbackQuery):
    """Показать инструкцию для конкретной платформы"""
    platform = callback.data.split("_")[1]
    
    if platform == "ios":
        app_link = "https://apps.apple.com/app/streisand/id6450534064"
        instructions = (
            "📱 *Установка на iPhone / iPad*\n\n"
            "1️⃣ Скачайте приложение **Streisand** из App Store:\n"
            f"[Открыть App Store]({app_link})\n\n"
            "2️⃣ Установите приложение\n\n"
            "3️⃣ Вернитесь в бота и нажмите **Получить ключ**\n\n"
            "4️⃣ Откройте полученную ссылку — Streisand автоматически импортирует конфигурацию\n\n"
            "5️⃣ Нажмите ▶️ для подключения\n\n"
            "✅ Готово!"
        )
    
    elif platform == "android":
        app_link = "https://play.google.com/store/apps/details?id=com.v2ray.ang"
        instructions = (
            "🤖 *Установка на Android*\n\n"
            "1️⃣ Скачайте приложение **V2RayNG** из Google Play:\n"
            f"[Открыть Google Play]({app_link})\n\n"
            "2️⃣ Установите приложение\n\n"
            "3️⃣ Вернитесь в бота и нажмите **Получить ключ**\n\n"
            "4️⃣ Нажмите на полученную ссылку — V2RayNG откроется и импортирует конфигурацию\n\n"
            "5️⃣ Нажмите ▶️ для подключения\n\n"
            "✅ Готово!"
        )
    
    elif platform == "mac":
        app_link = "https://github.com/yanue/V2rayU/releases"
        instructions = (
            "🍎 *Установка на Mac*\n\n"
            "1️⃣ Скачайте приложение **V2RayU** с GitHub:\n"
            f"[Скачать V2RayU]({app_link})\n\n"
            "2️⃣ Установите приложение (перетащите в папку Applications)\n\n"
            "3️⃣ Вернитесь в бота и нажмите **Получить ключ**\n\n"
            "4️⃣ Скопируйте полученную ссылку\n\n"
            "5️⃣ Откройте V2RayU → нажмите на иконку в строке меню → Import → Import from clipboard\n\n"
            "6️⃣ Нажмите Turn On\n\n"
            "✅ Готово!"
        )
    
    else:  # windows
        app_link = "https://github.com/2dust/v2rayN/releases"
        instructions = (
            "🪟 *Установка на Windows*\n\n"
            "1️⃣ Скачайте приложение **v2rayN** с GitHub:\n"
            f"[Скачать v2rayN]({app_link})\n\n"
            "2️⃣ Распакуйте архив и запустите v2rayN.exe\n\n"
            "3️⃣ Вернитесь в бота и нажмите **Получить ключ**\n\n"
            "4️⃣ Скопируйте полученную ссылку\n\n"
            "5️⃣ В v2rayN нажмите → Servers → Import from clipboard\n\n"
            "6️⃣ Нажмите Enter (кнопка включения)\n\n"
            "✅ Готово!"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Получить ключ", callback_data="get_key")],
        [InlineKeyboardButton(text="◀ Назад к выбору", callback_data="choose_platform")],
        [InlineKeyboardButton(text="◀ Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.answer(
        instructions,
        reply_markup=keyboard,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "get_key")
async def get_vpn_key(callback: types.CallbackQuery):
    """Получить VPN ключ для активной подписки (платной или пробной)"""
    user_id = callback.from_user.id
    
    async with AsyncSessionLocal() as session:
        subscription = await get_active_subscription(session, user_id)
        
        if not subscription:
            logger.warning(f"No active subscription for user {user_id}")
            await callback.answer(
                "❌ У вас нет активной подписки.\n\n"
                "Оформите пробный период или купите тариф в главном меню.",
                show_alert=True
            )
            return
        
        # Определяем название подписки с сервером
        server_name = "Frankfurt"
        
        if subscription.plan_id:
            plan = await get_plan(session, subscription.plan_id)
            plan_name = f"MILF VPN - {server_name} ({plan.name})"
        else:
            plan_name = f"MILF VPN - {server_name} (Trial)"
        
        # Форматируем дату и время
        end_date = subscription.end_date
        end_date_str = end_date.strftime('%d.%m.%Y')
        end_time_str = end_date.strftime('%H:%M')
        
        # Генерируем vless ссылку
        config_link = (
            f"vless://{subscription.client_id}@{VPN_SERVER_IP}:443"
            f"?type=tcp&security=reality"
            f"&pbk={VPN_REALITY_PUBLIC_KEY}&fp=chrome"
            f"&sni=www.cloudflare.com&sid={VPN_REALITY_SHORT_ID}"
            f"#{plan_name}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data=f"copy_link_{subscription.client_id}")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="instructions")]
        ])
        
        await callback.message.answer(
            f"🔑 *Ваш ключ подключения ({plan_name}):*\n\n"
            f"`{config_link}`\n\n"
            f"📅 *Действует до:* {end_date_str} в {end_time_str} МСК\n\n"
            f"📱 *Как подключиться:*\n"
            f"1️⃣ Скопируйте ссылку\n"
            f"2️⃣ Откройте приложение V2RayNG / Streisand\n"
            f"3️⃣ Нажмите + → Import from clipboard\n"
            f"4️⃣ Нажмите ▶️ для подключения",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        logger.info(f"Key sent to user {user_id}, expires at {subscription.end_date}")
        await callback.answer()


@router.callback_query(lambda c: c.data.startswith("copy_link_"))
async def copy_link_callback(callback: types.CallbackQuery):
    """Обработка кнопки копирования ссылки"""
    client_id = callback.data.split("_")[2]
    
    async with AsyncSessionLocal() as session:
        # Ищем подписку по client_id
        subscription = await session.execute(
            select(Subscription).where(Subscription.client_id == client_id)
        )
        subscription = subscription.scalar_one_or_none()
        
        # Если не нашли, ищем по user_id (для пробного периода)
        if not subscription:
            subscription = await session.execute(
                select(Subscription).where(
                    Subscription.user_id == callback.from_user.id,
                    Subscription.is_active == True,
                    Subscription.end_date > datetime.now()
                )
            )
            subscription = subscription.scalar_one_or_none()
        
        if not subscription:
            await callback.answer("❌ Подписка не найдена", show_alert=True)
            return
        
        # Определяем название подписки
        server_name = "Frankfurt"
        
        if subscription.plan_id:
            plan = await get_plan(session, subscription.plan_id)
            plan_name = f"MILF VPN - {server_name} ({plan.name})"
        else:
            plan_name = f"MILF VPN - {server_name} (Trial)"
        
        # Форматируем дату и время
        end_date = subscription.end_date
        end_date_str = end_date.strftime('%d.%m.%Y')
        end_time_str = end_date.strftime('%H:%M')
        
        # Генерируем ссылку
        config_link = (
            f"vless://{subscription.client_id}@{VPN_SERVER_IP}:443"
            f"?type=tcp&security=reality"
            f"&pbk={VPN_REALITY_PUBLIC_KEY}&fp=chrome"
            f"&sni=www.cloudflare.com&sid={VPN_REALITY_SHORT_ID}"
            f"#{plan_name}"
        )
        
        await callback.answer()
        await callback.message.answer(
            f"🔗 *Ваша ссылка для подключения ({plan_name}):*\n\n"
            f"`{config_link}`\n\n"
            f"📅 *Действует до:* {end_date_str} в {end_time_str} МСК\n\n"
            f"Скопируйте её и вставьте в приложение V2RayNG / Streisand.",
            parse_mode="Markdown"
        )
