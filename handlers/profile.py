from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.session import AsyncSessionLocal
from database.crud import get_user, get_user_active_subscription
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
        
        if subscription and not MOCK_MODE:
            # Получаем реальный статус из панели
            xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
            status = await xui.get_client(subscription.client_id)
            await xui.close()
            
            if status:
                usage_up = status.get('up', 0) / (1024**3)  # GB
                usage_down = status.get('down', 0) / (1024**3)
                total_usage = usage_up + usage_down
                
                profile_text = (
                    f"👤 *Профиль*\n\n"
                    f"🆔 ID: {user.user_id}\n"
                    f"📛 Username: @{user.username or 'нет'}\n"
                    f"💰 Баланс: {user.balance} ₽\n"
                    f"👥 Рефералов: {await get_referral_count(session, user.user_id)}\n\n"
                    f"📱 *Подписка:*\n"
                    f"📅 Действует до: {subscription.end_date.strftime('%d.%m.%Y')}\n"
                    f"📈 Использовано: {total_usage:.2f} GB\n"
                    f"⬆️ Исходящий: {usage_up:.2f} GB\n"
                    f"⬇️ Входящий: {usage_down:.2f} GB"
                )
            else:
                profile_text = f"👤 *Профиль*\n\n🆔 ID: {user.user_id}\n💰 Баланс: {user.balance} ₽\n\n❌ Не удалось получить статус подписки"
        else:
            profile_text = (
                f"👤 *Профиль*\n\n"
                f"🆔 ID: {user.user_id}\n"
                f"📛 Username: @{user.username or 'нет'}\n"
                f"💰 Баланс: {user.balance} ₽\n"
                f"👥 Рефералов: {await get_referral_count(session, user.user_id)}\n\n"
                f"📱 *Подписка:* {'Активна' if subscription else 'Нет активной подписки'}"
            )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="deposit")],
            [InlineKeyboardButton(text="📊 История транзакций", callback_data="history")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")]
        ])
        
        await callback.message.answer(
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
