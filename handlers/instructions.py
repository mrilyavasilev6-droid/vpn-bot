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
