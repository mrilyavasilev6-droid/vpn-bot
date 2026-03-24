from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.session import AsyncSessionLocal
from database.crud import get_user, get_user_active_subscription, get_plan
from vpn.xui import XUIClient
from config import MOCK_MODE, XUI_HOST, XUI_USERNAME, XUI_PASSWORD

router = Router()


@router.callback_query(lambda c: c.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    """Показать профиль пользователя"""
    async with AsyncSessionLocal() as session:
        user = await get_user(session, callback.from_user.id)
        
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        # Получаем активную подписку
        subscription = await get_user_active_subscription(session, callback.from_user.id)
        
        if subscription:
            end_date_str = subscription.end_date.strftime('%d.%m.%Y')
            
            # Получаем название плана (если есть)
            plan_name = "Пробный период"
            if subscription.plan_id:
                plan = await get_plan(session, subscription.plan_id)
                plan_name = plan.name if plan else "Подписка"
            
            if not MOCK_MODE:
                # Получаем реальный статус из панели
                xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
                status = await xui.get_client(subscription.client_id)
                await xui.close()
                
                if status:
                    usage_up = status.get('up', 0) / (1024**3)
                    usage_down = status.get('down', 0) / (1024**3)
                    total_usage = usage_up + usage_down
                    
                    profile_text = (
                        f"👤 *Профиль MILF VPN*\n\n"
                        f"🆔 ID: `{user.user_id}`\n"
                        f"📛 Username: @{user.username or 'нет'}\n"
                        f"💰 Баланс: {user.balance} ₽\n"
                        f"👥 Рефералов: {await get_referral_count(session, user.user_id)}\n\n"
                        f"📱 *Активная подписка:*\n"
                        f"📦 Тип: {plan_name}\n"
                        f"📅 Действует до: {end_date_str}\n"
                        f"📈 Использовано: {total_usage:.2f} GB\n"
                        f"⬆️ Исходящий: {usage_up:.2f} GB\n"
                        f"⬇️ Входящий: {usage_down:.2f} GB"
                    )
                else:
                    profile_text = (
                        f"👤 *Профиль MILF VPN*\n\n"
                        f"🆔 ID: `{user.user_id}`\n"
                        f"📛 Username: @{user.username or 'нет'}\n"
                        f"💰 Баланс: {user.balance} ₽\n"
                        f"👥 Рефералов: {await get_referral_count(session, user.user_id)}\n\n"
                        f"✅ *Активная подписка:* {plan_name}\n"
                        f"📅 Действует до: {end_date_str}"
                    )
            else:
                profile_text = (
                    f"👤 *Профиль MILF VPN*\n\n"
                    f"🆔 ID: `{user.user_id}`\n"
                    f"📛 Username: @{user.username or 'нет'}\n"
                    f"💰 Баланс: {user.balance} ₽\n"
                    f"👥 Рефералов: {await get_referral_count(session, user.user_id)}\n\n"
                    f"✅ *Активная подписка:* {plan_name}\n"
                    f"📅 Действует до: {end_date_str}"
                )
        else:
            profile_text = (
                f"👤 *Профиль MILF VPN*\n\n"
                f"🆔 ID: `{user.user_id}`\n"
                f"📛 Username: @{user.username or 'нет'}\n"
                f"💰 Баланс: {user.balance} ₽\n"
                f"👥 Рефералов: {await get_referral_count(session, user.user_id)}\n\n"
                f"📱 *Подписка:* Нет активной подписки\n\n"
                f"🔓 Попробуйте пробный период — 3 дня бесплатно!\n"
                f"💎 Или выберите тариф в разделе «Выбрать тариф»"
            )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Выбрать тариф", callback_data="subscription")],
            [InlineKeyboardButton(text="🔓 Пробный период", callback_data="trial_start")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            profile_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()


async def get_referral_count(session, user_id: int) -> int:
    """Получить количество рефералов"""
    from sqlalchemy import select, func
    from database.models import User
    
    result = await session.execute(
        select(func.count()).select_from(User).where(User.referral_by == user_id)
    )
    return result.scalar() or 0
