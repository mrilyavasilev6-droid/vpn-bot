from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.session import AsyncSessionLocal
from database.crud import get_user_active_subscription
from config import VPN_SERVER_IP, VPN_REALITY_PUBLIC_KEY, VPN_REALITY_SHORT_ID
from vpn.xui import XUIClient

router = Router()


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
    """Получить VPN ключ для активной подписки"""
    async with AsyncSessionLocal() as session:
        subscription = await get_user_active_subscription(session, callback.from_user.id)
        
        if not subscription:
            await callback.answer("❌ У вас нет активной подписки. Оформите пробный период или купите тариф.", show_alert=True)
            return
        
        # Получаем план
        from database.crud import get_plan
        plan = await get_plan(session, subscription.plan_id)
        plan_name = plan.name if plan else "VPN"
        
        # Генерируем ссылку
        xui = XUIClient(None, None, None)
        config_link = await xui.get_client_config(
            client_uuid=subscription.client_id,
            server_host=VPN_SERVER_IP,
            plan_name=plan_name,
            public_key=VPN_REALITY_PUBLIC_KEY,
            short_id=VPN_REALITY_SHORT_ID
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data=f"copy_link_{subscription.client_id}")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="instructions")]
        ])
        
        await callback.message.answer(
            f"🔑 *Ваш ключ подключения:*\n\n"
            f"`{config_link}`\n\n"
            f"📱 *Как подключиться:*\n"
            f"1. Нажмите на ссылку или скопируйте её\n"
            f"2. Приложение откроется автоматически\n"
            f"3. Нажмите ▶️ для подключения",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
