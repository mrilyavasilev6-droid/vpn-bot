from aiogram import Router, types
from sqlalchemy import select, func
from database.session import AsyncSessionLocal
from database.models import User, ReferralBonus

router = Router()

@router.callback_query(lambda c: c.data == "referral")
async def referral_info(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        ref_link = f"https://t.me/VPNMilfBot?start=ref_{user_id}"
        referrals_count = await session.execute(select(func.count()).where(User.referral_by == user_id))
        referrals_count = referrals_count.scalar() or 0
        bonus_days = await session.execute(select(func.sum(ReferralBonus.bonus_days)).where(ReferralBonus.referrer_id == user_id))
        bonus_days = bonus_days.scalar() or 0

        text = (
            "👥 <b>Реферальная программа</b>\n\n"
            "Приглашайте друзей и получайте бонусы!\n"
            "За каждого друга, который купит подписку, вы получите +7 дней к вашей подписке.\n\n"
            f"<b>Ваша ссылка:</b>\n{ref_link}\n\n"
            f"Приглашено друзей: {referrals_count}\n"
            f"Получено бонусных дней: {bonus_days}"
        )
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Поделиться", url=f"https://t.me/share/url?url={ref_link}&text=Привет! Подключай быстрый VPN по моей ссылке:")],
            [types.InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()
