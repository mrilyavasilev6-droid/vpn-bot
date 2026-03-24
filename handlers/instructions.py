from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.crud import get_user_active_subscription, get_plan
from database.models import Trial, Subscription
from config import VPN_SERVER_IP, VPN_REALITY_PUBLIC_KEY, VPN_REALITY_SHORT_ID
import logging

router = Router()
logger = logging.getLogger(__name__)


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
        app_name = "Streisand"
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
        app_name = "V2RayNG"
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
        app_name = "V2RayU"
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
        app_name = "v2rayN"
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
        # 1. Проверяем активную платную подписку
        subscription = await get_user_active_subscription(session, user_id)
        
        # 2. Если нет платной, проверяем пробную подписку
        if not subscription:
            logger.info(f"No active subscription for user {user_id}, checking trial...")
            
            # Находим активную триальную подписку
            trial = await session.execute(
                select(Trial).where(
                    Trial.user_id == user_id,
                    Trial.is_active == True,
                    Trial.end_date > datetime.now()
                )
            )
            trial = trial.scalar_one_or_none()
            
            if trial:
                logger.info(f"Found active trial for user {user_id}, ends at {trial.end_date}")
                
                # Находим связанную подписку по client_id
                # Для пробного периода client_id = f"trial_{user_id}" или другой формат
                # Нужно искать в Subscription с этим user_id
                subscription = await session.execute(
                    select(Subscription).where(
                        Subscription.user_id == user_id,
                        Subscription.is_active == True,
                        Subscription.end_date > datetime.now()
                    )
                )
                subscription = subscription.scalar_one_or_none()
                
                if subscription:
                    logger.info(f"Found trial subscription for user {user_id}")
        
        if not subscription:
            logger.warning(f"No active subscription or trial for user {user_id}")
            await callback.answer(
                "❌ У вас нет активной подписки.\n\n"
                "Оформите пробный период или купите тариф в главном меню.",
                show_alert=True
            )
            return
        
        # Определяем название подписки
        plan_name = "Пробный период"
        if subscription.plan_id:
            plan = await get_plan(session, subscription.plan_id)
            plan_name = plan.name if plan else "VPN"
        
        # Генерируем vless ссылку
        config_link = (
            f"vless://{subscription.client_id}@{VPN_SERVER_IP}:443"
            f"?type=tcp&security=reality"
            f"&pbk={VPN_REALITY_PUBLIC_KEY}&fp=chrome"
            f"&sni=www.cloudflare.com&sid={VPN_REALITY_SHORT_ID}"
            f"#{plan_name.replace(' ', '_')}"
        )
        
        # Кнопка копирования
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data=f"copy_link_{subscription.client_id}")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="instructions")]
        ])
        
        await callback.message.answer(
            f"🔑 *Ваш ключ подключения ({plan_name}):*\n\n"
            f"`{config_link}`\n\n"
            f"📅 *Действует до:* {subscription.end_date.strftime('%d.%m.%Y')}\n\n"
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
            select(Subscription).where(
                Subscription.client_id == client_id,
                Subscription.is_active == True
            )
        )
        subscription = subscription.scalar_one_or_none()
        
        if not subscription:
            await callback.answer("Подписка не найдена", show_alert=True)
            return
        
        # Определяем название подписки
        plan_name = "Пробный период"
        if subscription.plan_id:
            plan = await get_plan(session, subscription.plan_id)
            plan_name = plan.name if plan else "VPN"
        
        # Генерируем ссылку
        config_link = (
            f"vless://{subscription.client_id}@{VPN_SERVER_IP}:443"
            f"?type=tcp&security=reality"
            f"&pbk={VPN_REALITY_PUBLIC_KEY}&fp=chrome"
            f"&sni=www.cloudflare.com&sid={VPN_REALITY_SHORT_ID}"
            f"#{plan_name.replace(' ', '_')}"
        )
        
        await callback.answer()
        await callback.message.answer(
            f"🔗 *Ваша ссылка для подключения:*\n\n"
            f"`{config_link}`\n\n"
            f"📅 Действует до: {subscription.end_date.strftime('%d.%m.%Y')}\n\n"
            f"Скопируйте её и вставьте в приложение V2RayNG / Streisand.",
            parse_mode="Markdown"
        )
