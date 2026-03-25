from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.crud import get_plan
from database.models import Trial, Subscription
from config import VPN_SERVER_IP, XUI_HOST, XUI_USERNAME, XUI_PASSWORD, SERVERS, REALITY_SNI, REALITY_FINGERPRINT, SUBSCRIPTION_URL
from vpn.xui import XUIClient
import logging

router = Router()
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
        # Если есть Trial, ищем связанную подписку
        sub = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.end_date == trial.end_date
            )
        )
        subscription = sub.scalar_one_or_none()
        if subscription:
            return subscription
    
    return None


@router.callback_query(lambda c: c.data == "instructions")
async def instructions_start(callback: types.CallbackQuery):
    """Показать общую инструкцию"""
    text = (
        "📖 *Инструкция по установке MILF VPN*\n\n"
        "1️⃣ В Главном меню выберите **Пробный период** или оформите **Подписку**\n\n"
        "2️⃣ После активации вы получите ссылку-подписку\n\n"
        "3️⃣ Скачайте приложение для вашей платформы:\n"
        "   • iPhone / iPad — Streisand\n"
        "   • Android — V2RayNG\n"
        "   • Mac — V2RayU\n"
        "   • Windows — v2rayN\n\n"
        "4️⃣ В приложении нажмите + → Add Subscription\n\n"
        "5️⃣ Вставьте полученную ссылку\n\n"
        "6️⃣ Нажмите обновить — появятся все серверы\n\n"
        "7️⃣ Нажмите ▶️ на любом сервере для подключения\n\n"
        "✅ Готово! Интернет защищён.\n\n"
        "✨ *Доступные серверы:*\n"
        "🇩🇪 Германия | 🇮🇳 Индия | 🇷🇺 Россия СПБ | 🇮🇹 Италия | 🇹🇷 Турция"
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
            "4️⃣ В Streisand нажмите + → Add Subscription\n"
            "5️⃣ Вставьте ссылку\n"
            "6️⃣ Нажмите обновить\n"
            "7️⃣ Нажмите ▶️ для подключения\n\n"
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
            "4️⃣ В V2RayNG нажмите + → Add Subscription\n"
            "5️⃣ Вставьте ссылку\n"
            "6️⃣ Нажмите обновить\n"
            "7️⃣ Нажмите ▶️ для подключения\n\n"
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
            "4️⃣ Скопируйте ссылку-подписку\n\n"
            "5️⃣ Откройте V2RayU → нажмите на иконку в строке меню → Subscription → Add\n"
            "6️⃣ Вставьте ссылку\n"
            "7️⃣ Нажмите Turn On\n\n"
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
            "4️⃣ Скопируйте ссылку-подписку\n\n"
            "5️⃣ В v2rayN нажмите → Subscription → Add\n"
            "6️⃣ Вставьте ссылку\n"
            "7️⃣ Нажмите Enter (кнопка включения)\n\n"
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
    """Получить ссылку-подписку для активной подписки"""
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
        
        # Используем единую ссылку-подписку
        sub_link = SUBSCRIPTION_URL
        
        # Определяем название подписки
        if subscription.plan_id:
            plan = await get_plan(session, subscription.plan_id)
            plan_name = f"MILF VPN ({plan.name})"
        else:
            plan_name = "MILF VPN (Trial)"
        
        # Форматируем дату и время
        end_date = subscription.end_date
        end_date_str = end_date.strftime('%d.%m.%Y')
        end_time_str = end_date.strftime('%H:%M')
        
        # Получаем суммарный использованный трафик по всем серверам
        total_usage = 0
        try:
            xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
            client_stats = await xui.get_client(subscription.client_id)
            if client_stats:
                total_usage = (client_stats.get('up', 0) + client_stats.get('down', 0)) / (1024**3)
            await xui.close()
        except Exception as e:
            logger.error(f"Error getting client stats: {e}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data=f"copy_sub_{subscription.client_id}")],
            [InlineKeyboardButton(text="📱 Добавить в V2RayNG", url=sub_link)],
            [InlineKeyboardButton(text="◀ Назад", callback_data="instructions")]
        ])
        
        # Список серверов для отображения
        servers_list = " | ".join([s['name'] for s in SERVERS])
        
        await callback.message.answer(
            f"🔑 *{plan_name}*\n\n"
            f"🔗 *Ссылка-подписка:*\n`{sub_link}`\n\n"
            f"📊 *Использовано:* {total_usage:.2f} GB\n"
            f"📅 *Действует до:* {end_date_str} в {end_time_str} МСК\n\n"
            f"📱 *Как добавить в V2RayNG:*\n"
            f"1️⃣ Нажмите + → Add Subscription\n"
            f"2️⃣ Вставьте ссылку\n"
            f"3️⃣ Нажмите обновить\n\n"
            f"✨ *Доступные серверы:*\n{servers_list}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        logger.info(f"Subscription link sent to user {user_id}, expires at {subscription.end_date}")
        await callback.answer()


@router.callback_query(lambda c: c.data.startswith("copy_sub_"))
async def copy_sub_link(callback: types.CallbackQuery):
    """Скопировать ссылку-подписку"""
    client_id = callback.data.split("_")[2]
    sub_link = SUBSCRIPTION_URL
    
    servers_list = " | ".join([s['name'] for s in SERVERS])
    
    await callback.answer()
    await callback.message.answer(
        f"🔗 *Ваша ссылка-подписка:*\n`{sub_link}`\n\n"
        f"Скопируйте её и вставьте в V2RayNG → Add Subscription.\n\n"
        f"✨ После добавления у вас появятся все серверы:\n{servers_list}",
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data.startswith("copy_link_"))
async def copy_link_callback(callback: types.CallbackQuery):
    """Обработка кнопки копирования ссылки (старый формат, для совместимости)"""
    sub_link = SUBSCRIPTION_URL
    
    servers_list = " | ".join([s['name'] for s in SERVERS])
    
    await callback.answer()
    await callback.message.answer(
        f"🔗 *Ваша ссылка-подписка:*\n`{sub_link}`\n\n"
        f"Скопируйте её и вставьте в V2RayNG → Add Subscription.\n\n"
        f"✨ После добавления у вас появятся все серверы:\n{servers_list}",
        parse_mode="Markdown"
    )
