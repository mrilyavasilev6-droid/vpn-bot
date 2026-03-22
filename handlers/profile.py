from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from database.session import AsyncSessionLocal
from database.models import User, Subscription, Plan, ReferralBonus
import datetime

router = Router()

@router.callback_query(lambda c: c.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        # Активная подписка
        sub = await session.execute(
            select(Subscription, Plan)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(Subscription.user_id == user_id, Subscription.is_active == True)
        )
        sub_data = sub.first()
        if sub_data:
            subscription, plan = sub_data
            days_left = (subscription.end_date - datetime.datetime.now()).days
            sub_text = f"Активен: {plan.name}, до {subscription.end_date.strftime('%d.%m.%Y')} (осталось {days_left} дн.)"
        else:
            sub_text = "Нет активной подписки"

        # Количество приглашённых
        referrals = await session.execute(select(func.count()).where(User.referral_by == user_id))
        referrals_count = referrals.scalar() or 0

        # Сумма бонусных дней
        bonuses = await session.execute(select(func.sum(ReferralBonus.bonus_days)).where(ReferralBonus.referrer_id == user_id))
        bonus_days = bonuses.scalar() or 0
        discount = bonus_days // 30

        # Реферальная ссылка
        ref_link = f"https://t.me/VPNMilfBot?start=ref_{user_id}"

        text = (
            f"<b># PERSONAL ACCOUNT</b>\n"
            f"<b>ЛИЧНЫЙ КАБИНЕТ</b>\n\n"
            f"<b>Терминал пользователя</b>\n"
            f"ID: {user_id}\n\n"
            f"<b>Автопродление:</b> {'Включено ✅' if user.auto_renew else 'Выключено ❌'}\n"
            f"Друзей в системе: {referrals_count} {'❌' if referrals_count == 0 else ''}\n"
            f"Ваша скидка: {discount}%\n\n"
            f"<b>Баланс:</b> {user.balance/100:.2f} ₽ {'❌' if user.balance == 0 else ''}\n"
            f"Траты друзей: 0.0 ₽\n"
            f"Расходы: 0.0 ₽\n\n"
            f"<b>Ваша реферальная ссылка:</b>\n{ref_link}\n\n"
            "---\n"
            f"<b>Мои подписки</b>\n{sub_text}\n"
            "🔹 Продать подписку\n"
            f"🔹 Автопродление: {'ВКЛ' if user.auto_renew else 'ВЫКЛ'}\n\n"
            "<b>Пополнить баланс</b>\n"
            "🔹 История платежей\n\n"
            "🔙 Вернуться в главное меню"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Автопродление", callback_data="toggle_auto_renew")],
            [InlineKeyboardButton(text="Пополнить баланс", callback_data="deposit")],
            [InlineKeyboardButton(text="История платежей", callback_data="payments_history")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(lambda c: c.data == "toggle_auto_renew")
async def toggle_auto_renew(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        user.auto_renew = not user.auto_renew
        await session.commit()
    await callback.answer(f"Автопродление {'включено' if user.auto_renew else 'выключено'}")
    await show_profile(callback)

@router.callback_query(lambda c: c.data == "deposit")
async def deposit(callback: types.CallbackQuery):
    await callback.message.answer("Функция пополнения баланса в разработке.")
    await callback.answer()

@router.callback_query(lambda c: c.data == "payments_history")
async def payments_history(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        from database.models import Transaction
        txs = await session.execute(
            select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.created_at.desc()).limit(10)
        )
        txs = txs.scalars().all()
        if not txs:
            await callback.message.answer("История платежей пуста.")
            return
        text = "<b>История платежей:</b>\n"
        for tx in txs:
            amount = tx.amount / 100 if tx.currency == 'RUB' else tx.amount
            text += f"{tx.created_at.strftime('%d.%m.%Y %H:%M')} — {amount} {tx.currency} ({tx.payment_method})\n"
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()
