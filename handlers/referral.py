from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy import select
from database import get_session, User, ReferralBonus, Subscription, Plan
import datetime

router = Router()

@router.message(Command('referral'))
async def show_referral_link(message: types.Message):
    """Показывает реферальную ссылку пользователя"""
    user_id = message.from_user.id
    link = f"https://t.me/VPNMilfBot?start=ref_{user_id}"
    await message.answer(
        f"Ваша реферальная ссылка:\n{link}\n"
        "За каждого друга, купившего подписку, вы получите +7 дней к вашей подписке!"
    )