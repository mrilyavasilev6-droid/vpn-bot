from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

@router.callback_query(lambda c: c.data.startswith("inst_"))
async def show_instruction(callback: types.CallbackQuery):
    data = callback.data.split("_")
    platform = data[1]
    client_id = data[2] if len(data) > 2 else None

    if platform == "android":
        app_link = "https://play.google.com/store/apps/details?id=com.v2raytun.android&hl=ru"
        text = (
            "Приложение v2RayTun в Google Play\n\n"
            f"Скачать приложение: {app_link}\n\n"
            "✅ Установлено, к следующему шагу"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Установлено, к следующему шагу", callback_data=f"next_{client_id}")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="trial_start")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)

    elif platform == "ios":
        app_link = "https://apps.apple.com/app/streisand/id6450534064"
        text = (
            "Приложение Streisand в App Store\n\n"
            f"Скачать приложение: {app_link}\n\n"
            "✅ Установлено, к следующему шагу"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Установлено, к следующему шагу", callback_data=f"next_{client_id}")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="trial_start")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)

    elif platform == "mac":
        text = "Для Mac используйте приложение V2RayU\n\nСкачать: https://github.com/yanue/V2rayU/releases"
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее", callback_data=f"next_{client_id}")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="trial_start")]
        ]))
    elif platform == "windows":
        text = "Для Windows используйте приложение v2rayN\n\nСкачать: https://github.com/2dust/v2rayN/releases"
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее", callback_data=f"next_{client_id}")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="trial_start")]
        ]))

    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("next_"))
async def show_config(callback: types.CallbackQuery):
    client_id = callback.data.split("_")[1]

    # Здесь нужно сгенерировать реальную ссылку на конфиг из VPN-панели
    # Для примера используем ссылку-заглушку
    config_link = f"https://ваш-домен/get_config/{client_id}"

    text = (
        "2️⃣ Запустите приложение\n\n"
        "3️⃣ Откройте ссылку с ключом, которая появится ниже, ключ добавится автоматически в приложение\n\n"
        "Конфигурация будет доступена в течение 2 минут!\n\n"
        "Далее нажмите кнопку подключения в приложении, оно запросит доступ к конфигурации телефона, разрешите доступ.\n"
        "Снова нажмите кнопку подключения\n\n"
        f"🔔 [Получить конфигурацию]({config_link})\n\n"
        "✅ Все получилось"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)
    await callback.answer()
