from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy import select
from database.session import get_session
from database.models import Subscription, Plan, Server
import datetime

router = Router()

@router.message(Command('profile'))
async def profile(message: types.Message):
    user_id = message.from_user.id
    async with get_session() as session:
        result = await session.execute(
            select(Subscription, Plan, Server)
            .join(Plan, Subscription.plan_id == Plan.id)
            .join(Server, Subscription.server_id == Server.id)
            .where(Subscription.user_id == user_id, Subscription.is_active == True)
        )
        row = result.first()
        if not row:
            await message.answer("У вас нет активной подписки. /buy для покупки.")
            return
        sub, plan, server = row
        days_left = (sub.end_date - datetime.datetime.now()).days
        text = (
            f"📋 Ваш тариф: {plan.name}\n"
            f"📅 Действует до: {sub.end_date.strftime('%d.%m.%Y')}\n"
            f"⏳ Осталось дней: {days_left}\n"
            f"🖥 Сервер: {server.name} ({server.location})\n"
        )
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Продлить", callback_data="extend")],
            [types.InlineKeyboardButton(text="📥 Скачать конфиг", callback_data="get_config")],
            [types.InlineKeyboardButton(text="🌍 Сменить сервер", callback_data="change_server")]
        ])
        await message.answer(text, reply_markup=keyboard)