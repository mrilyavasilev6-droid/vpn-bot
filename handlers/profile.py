from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from sqlalchemy import select, func
from database.session import AsyncSessionLocal
from database.crud import get_user, get_user_active_subscription, get_plan
from database.models import User, Trial, Subscription
from vpn.xui import XUIClient
from config import MOCK_MODE, XUI_HOST, XUI_USERNAME, XUI_PASSWORD, SERVERS
import logging

router = Router()
logger = logging.getLogger(__name__)


async def get_referral_count(session, user_id: int) -> int:
    """Получить количество рефералов"""
    result = await session.execute(
        select(func.count()).select_from(User).where(User.referral_by == user_id)
    )
    return result.scalar() or 0


async def get_server_count() -> int:
    """Получить количество доступных серверов"""
    return len(SERVERS)


@router.callback_query(lambda c: c.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    """Показать профиль пользователя"""
    async with AsyncSessionLocal() as session:
        user = await get_user(session, callback.from_user.id)
        
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        # Проверяем активную платную подписку
        subscription = await get_user_active_subscription(session, callback.from_user.id)
        
        # Если нет платной подписки, проверяем пробный период
        if not subscription:
            active_trial = await session.execute(
                select(Trial).where(
                    Trial.user_id == callback.from_user.id,
                    Trial.is_active == True,
                    Trial.end_date > datetime.now()
                )
            )
            active_trial = active_trial.scalar_one_or_none()
            
            if active_trial:
                # Ищем связанную Subscription по end_date
                subscription = await session.execute(
                    select(Subscription).where(
                        Subscription.user_id == callback.from_user.id,
                        Subscription.end_date == active_trial.end_date,
                        Subscription.is_active == True
                    )
                )
                subscription = subscription.scalar_one_or_none()
        
        # Получаем количество серверов
        servers_count = await get_server_count()
        servers_list = "\n".join([f"  {s['name']}" for s in SERVERS[:5]])
        if servers_count > 5:
            servers_list += f"\n  ... и ещё {servers_count - 5} серверов"
        
        if subscription:
            end_date_str = subscription.end_date.strftime('%d.%m.%Y')
            end_time_str = subscription.end_date.strftime('%H:%M')
            
            # Определяем тип подписки
            if subscription.plan_id:
                plan = await get_plan(session, subscription.plan_id)
                plan_name = plan.name if plan else "Подписка"
            else:
                plan_name = "🔓 Пробный период"
            
            # Получаем использование из панели
            usage_text = ""
            if not MOCK_MODE and subscription.client_id and not subscription.client_id.startswith('mock'):
                try:
                    xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
                    status = await xui.get_client(subscription.client_id)
                    await xui.close()
                    if status:
                        total_usage = (status.get('up', 0) + status.get('down', 0)) / (1024**3)
                        usage_text = f"\n📈 Использовано: {total_usage:.2f} GB"
                except Exception as e:
                    logger.error(f"Error getting usage: {e}")
            
            profile_text = (
                f"👤 *Профиль MILF VPN*\n\n"
                f"🆔 ID: {user.user_id}\n"
                f"📛 Username: @{user.username or 'нет'}\n"
                f"💰 Баланс: {user.balance} ₽\n"
                f"👥 Рефералов: {await get_referral_count(session, user.user_id)}\n\n"
                f"📱 *Активная подписка:* {plan_name}\n"
                f"📅 Действует до: {end_date_str} в {end_time_str} МСК{usage_text}\n\n"
                f"🌍 *Доступные серверы:*\n{servers_list}\n\n"
                f"⚡ *Совет:* Выбирайте сервер с наименьшим пингом для лучшей скорости."
            )
        else:
            profile_text = (
                f"👤 *Профиль MILF VPN*\n\n"
                f"🆔 ID: {user.user_id}\n"
                f"📛 Username: @{user.username or 'нет'}\n"
                f"💰 Баланс: {user.balance} ₽\n"
                f"👥 Рефералов: {await get_referral_count(session, user.user_id)}\n\n"
                f"📱 *Подписка:* Нет активной подписки\n\n"
                f"🌍 *Доступные серверы:*\n{servers_list}\n\n"
                f"🔓 *Попробуйте пробный период — 3 дня бесплатно!*\n"
                f"💎 *Или выберите тариф в разделе «Выбрать тариф»*"
            )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Выбрать тариф", callback_data="subscription")],
            [InlineKeyboardButton(text="🔓 Пробный период", callback_data="trial_start")],
            [InlineKeyboardButton(text="🌍 Список серверов", callback_data="server_list")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")]
        ])
        
        # Используем edit_text, но с защитой от ошибки
        try:
            await callback.message.edit_text(
                profile_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception:
            # Если не удалось отредактировать (например, сообщение с фото), отправляем новое
            await callback.message.answer(
                profile_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        await callback.answer()


@router.callback_query(lambda c: c.data == "server_list")
async def show_server_list(callback: types.CallbackQuery):
    """Показать подробный список серверов"""
    servers_text = ""
    for i, server in enumerate(SERVERS, 1):
        servers_text += f"{i}. {server['name']}\n"
        servers_text += f"   📡 Порт: {server['port']}\n\n"
    
    text = (
        "🌍 *Серверы MILF VPN*\n\n"
        f"{servers_text}\n"
        "⚡ *Совет:* Выбирайте сервер с наименьшим пингом.\n"
        "🔄 Для смены сервера просто нажмите на другую конфигурацию в приложении."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="profile")]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()
