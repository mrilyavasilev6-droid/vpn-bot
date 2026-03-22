from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

router = Router()

def get_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 Пробный период", callback_data="trial_start")],
        [InlineKeyboardButton(text="💎 Подписка", callback_data="subscription")],
        [InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="referral")],
        [InlineKeyboardButton(text="📖 Инструкция по установке", callback_data="instructions")],
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")],
        [InlineKeyboardButton(text="❓ Поддержка", callback_data="support")]
    ])

async def show_main_menu(message: types.Message):
    text = (
        "**HOT VPN**\nБыстрый и стабильный\n\n"
        "**HOT VPN**\nГлавное меню бота\n\n"
        "Начните с Пробного периода, чтобы оценить работу прежде чем оплатить тариф\n\n"
        "Используя сервис вы соглашаетесь с офертой, политикой конфиденциальности и правилами"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

@router.callback_query(lambda c: c.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery):
    await show_main_menu(callback.message)
    await callback.answer()

@router.callback_query(lambda c: c.data == "support")
async def support(callback: types.CallbackQuery):
    await callback.message.answer(
        "По всем вопросам обращайтесь к @support_username\n"
        "Или напишите на support@example.com"
    )
    await callback.answer()
