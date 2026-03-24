from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS
import json
import os

router = Router()


class FeedbackState(StatesGroup):
    waiting_for_message = State()


@router.callback_query(lambda c: c.data == "feedback_start")
async def feedback_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать обратную связь"""
    text = (
        "📝 *Напишите ваше сообщение*\n\n"
        "Опишите проблему или задайте вопрос.\n"
        "Я передам его администратору.\n\n"
        "✏️ *Введите ваше сообщение:*"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Отмена", callback_data="support")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(FeedbackState.waiting_for_message)
    await callback.answer()


@router.message(FeedbackState.waiting_for_message)
async def feedback_get_message(message: types.Message, state: FSMContext):
    """Получить сообщение от пользователя и переслать админу"""
    user_id = message.from_user.id
    username = message.from_user.username or "нет username"
    user_link = f"tg://user?id={user_id}"
    
    feedback_text = (
        f"📩 *Новое сообщение в поддержку*\n\n"
        f"👤 *Пользователь:* @{username}\n"
        f"🆔 *ID:* `{user_id}`\n\n"
        f"💬 *Сообщение:*\n{message.text}"
    )
    
    # Отправляем админам
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                feedback_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✏️ Ответить", callback_data=f"reply_{user_id}")]
                ])
            )
        except Exception as e:
            print(f"Ошибка отправки админу {admin_id}: {e}")
    
    # Подтверждение пользователю
    await message.answer(
        "✅ *Сообщение отправлено!*\n\n"
        "Администратор ответит вам в ближайшее время.\n"
        "Ответ придёт в этот чат.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀ Главное меню", callback_data="main_menu")]
        ])
    )
    
    await state.clear()
