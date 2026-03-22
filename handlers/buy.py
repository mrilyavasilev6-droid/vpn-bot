from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.session import get_session
from database.crud import get_all_plans

router = Router()

@router.message(Command('buy'))
async def show_plans(message: types.Message):
    async with get_session() as session:
        plans = await get_all_plans(session)
        if not plans:
            await message.answer("Тарифы временно недоступны.")
            return

        builder = InlineKeyboardBuilder()
        for p in plans:
            builder.button(text=f"{p.name} — {p.price_stars}⭐ / {p.price_rub/100}₽", callback_data=f"plan_{p.id}")
        builder.adjust(1)
        await message.answer("Выберите тариф:", reply_markup=builder.as_markup())

@router.callback_query(lambda c: c.data.startswith('plan_'))
async def plan_selected(callback: types.CallbackQuery):
    plan_id = int(callback.data.split('_')[1])
    async with get_session() as session:
        from database.crud import get_active_plan
        plan = await get_active_plan(session, plan_id)
        if not plan:
            await callback.answer("Тариф не найден")
            return

    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Telegram Stars", callback_data=f"pay_stars_{plan_id}")
    builder.button(text="💳 Карта (ЮKassa)", callback_data=f"pay_card_{plan_id}")
    builder.adjust(1)

    await callback.message.edit_text(
        f"Тариф: {plan.name}\n"
        f"Срок: {plan.duration_days} дней\n"
        f"Стоимость: {plan.price_stars}⭐ или {plan.price_rub/100}₽\n\n"
        "Выберите способ оплаты:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()