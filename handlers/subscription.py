from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.models import Plan
from config import PROVIDER_TOKEN

router = Router()

@router.callback_query(lambda c: c.data == "subscription")
async def show_subscription_plans(callback: types.CallbackQuery):
    async with AsyncSessionLocal() as session:
        plans = await session.execute(select(Plan).where(Plan.is_active == True))
        plans = plans.scalars().all()
        if not plans:
            await callback.message.answer("Тарифы временно недоступны.")
            return

        text = "**Выберите тарифный план**\n\nЧем больше период, тем выгоднее стоимость.\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for p in plans:
            text += f"{p.name} - {p.price_rub/100} руб.\n"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=f"{p.name} - {p.price_rub/100} руб.", callback_data=f"buy_{p.id}")
            ])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")])
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    plan_id = int(callback.data.split("_")[1])
    async with AsyncSessionLocal() as session:
        plan = await session.get(Plan, plan_id)
        if not plan:
            await callback.answer("Тариф не найден")
            return

    # Создаём инвойс для оплаты рублями (ЮKassa)
    await callback.message.answer_invoice(
        title=plan.name,
        description=plan.description or f"VPN подписка на {plan.duration_days} дней",
        payload=f"plan_{plan_id}_{callback.from_user.id}",
        provider_token=PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label=plan.name, amount=plan.price_rub)],
        start_parameter="vpn_subscription",
        need_email=True,
        need_phone_number=True
    )
    await callback.answer()
