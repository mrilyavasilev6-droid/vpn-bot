from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.session import AsyncSessionLocal
from database.crud import get_all_active_plans, get_user
from config import PROVIDER_TOKEN

router = Router()


@router.callback_query(lambda c: c.data == "subscription")
async def show_subscription_plans(callback: types.CallbackQuery):
    """Показать тарифы подписки"""
    async with AsyncSessionLocal() as session:
        plans = await get_all_active_plans(session)
        
        if not plans:
            await callback.answer("Тарифы временно недоступны", show_alert=True)
            return
        
        keyboard = []
        for plan in plans:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{plan.name} — {plan.price_stars} ⭐ ({plan.duration_days} дн.)",
                    callback_data=f"buy_plan_{plan.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")])
        
        await callback.message.edit_text(
            "💎 *Выберите тариф:*\n\n"
            "Оплата производится звёздами Telegram.\n"
            "После оплаты вы получите ссылку для подключения.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )
        await callback.answer()


@router.callback_query(lambda c: c.data.startswith("buy_plan_"))
async def buy_plan(callback: types.CallbackQuery):
    """Создать инвойс для оплаты"""
    plan_id = int(callback.data.split("_")[2])
    
    async with AsyncSessionLocal() as session:
        from database.crud import get_plan
        plan = await get_plan(session, plan_id)
        
        if not plan:
            await callback.answer("Тариф не найден", show_alert=True)
            return
        
        user = await get_user(session, callback.from_user.id)
        if not user:
            from database.crud import create_user
            user = await create_user(session, callback.from_user.id, callback.from_user.username)
        
        # Формируем инвойс
        prices = [types.LabeledPrice(label=plan.name, amount=plan.price_stars)]
        payload = f"plan_{plan.id}_{callback.from_user.id}"
        
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Подписка {plan.name}",
            description=f"Доступ к VPN на {plan.duration_days} дней",
            payload=payload,
            provider_token=PROVIDER_TOKEN,
            currency="XTR",
            prices=prices,
            start_parameter=f"buy_{plan.id}"
        )
        await callback.answer()
