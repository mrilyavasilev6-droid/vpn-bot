from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import VPN_SERVER_IP
from vpn.xui import XUIClient
from database.session import AsyncSessionLocal
from database.crud import get_user_active_subscription

router = Router()


@router.callback_query(lambda c: c.data.startswith("inst_"))
async def show_instruction(callback: types.CallbackQuery):
    data = callback.data.split("_")
    platform = data[1]
    client_id = data[2] if len(data) > 2 else None

    if platform == "android":
        app_link = "https://play.google.com/store/apps/details?id=com.v2raytun.android&hl=ru"
        text = (
            f"📱 *Установка на Android*\n\n"
            f"1. Скачайте приложение V2RayNG:\n{app_link}\n\n"
            f"2. Установите приложение\n\n"
            f"✅ После установки нажмите кнопку ниже"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Установлено, далее", callback_data=f"next_{client_id}")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="trial_start")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)

    elif platform == "ios":
        app_link = "https://apps.apple.com/app/streisand/id6450534064"
        text = (
            f"📱 *Установка на iOS*\n\n"
            f"1. Скачайте приложение Streisand:\n{app_link}\n\n"
            f"2. Установите приложение\n\n"
            f"✅ После установки нажмите кнопку ниже"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Установлено, далее", callback_data=f"next_{client_id}")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="trial_start")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)

    elif platform == "mac":
        text = "🍎 *Установка на Mac*\n\nИспользуйте приложение V2RayU\n\nСкачать: https://github.com/yanue/V2rayU/releases"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Далее", callback_data=f"next_{client_id}")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="trial_start")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    elif platform == "windows":
        text = "🪟 *Установка на Windows*\n\nИспользуйте приложение v2rayN\n\nСкачать: https://github.com/2dust/v2rayN/releases"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Далее", callback_data=f"next_{client_id}")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="trial_start")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("next_"))
async def show_config(callback: types.CallbackQuery):
    """Показать конфигурацию VPN"""
    client_id = callback.data.split("_")[1]

    # Получаем подписку из БД
    async with AsyncSessionLocal() as session:
        subscription = await get_user_active_subscription(session, callback.from_user.id)
        
        if not subscription:
            await callback.message.answer("❌ У вас нет активной подписки")
            return
        
        # Получаем план для имени
        from database.crud import get_plan
        plan = await get_plan(session, subscription.plan_id)
        plan_name = plan.name if plan else "VPN"
    
    # Генерируем реальную ссылку
    from config import XUI_HOST, XUI_USERNAME, XUI_PASSWORD, VPN_SERVER_IP, VPN_REALITY_PUBLIC_KEY, VPN_REALITY_SHORT_ID
    from vpn.xui import XUIClient
    
    xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
    config_link = await xui.get_client_config(
        client_uuid=subscription.client_id,
        server_host=VPN_SERVER_IP,
        plan_name=plan_name,
        public_key=VPN_REALITY_PUBLIC_KEY,
        short_id=VPN_REALITY_SHORT_ID
    )
    await xui.close()

    text = (
        "🔗 *Ваша конфигурация VPN*\n\n"
        f"`{config_link}`\n\n"
        "📱 *Как подключиться:*\n"
        "1. Откройте приложение V2RayNG / Streisand\n"
        "2. Нажмите кнопку + (добавить)\n"
        "3. Выберите «Import from clipboard»\n"
        "4. Нажмите ▶️ для подключения\n\n"
        "✅ Готово! Интернет защищён."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data=f"copy_vpn_{subscription.client_id}")],
        [InlineKeyboardButton(text="◀ Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()
