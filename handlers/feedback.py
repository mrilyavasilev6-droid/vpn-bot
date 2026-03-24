from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS
import json
import os

router = Router()

# Файл для хранения непрочитанных сообщений
PENDING_FILE = "pending_messages.json"

def save_pending(message_data):
    """Сохранить сообщение в очередь"""
    pending = []
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, 'r') as f:
            try:
                pending = json.load(f)
            except:
                pass
    
    pending.append(message_data)
    with open(PENDING_FILE, 'w') as f:
        json.dump(pending, f, indent=2)


def get_pending():
    """Получить все непрочитанные сообщения"""
    if not os.path.exists(PENDING_FILE):
        return []
    with open(PENDING_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return []


def clear_pending():
    """Очистить очередь"""
    if os.path.exists(PENDING_FILE):
        os.remove(PENDING_FILE)


class SupportState(StatesGroup):
    waiting_for_reply = State()


@router.callback_query(lambda c: c.data == "support")
async def support_menu(callback: types.CallbackQuery):
    """Показать меню поддержки для пользователя"""
    text = (
        "📞 *Поддержка MILF VPN*\n\n"
        "Напишите ваше сообщение ниже.\n"
        "Администратор ответит вам в ближайшее время.\n\n"
        "✏️ *Введите ваше сообщение:*"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.message(lambda m: m.text and not m.text.startswith('/'))
async def handle_user_message(message: types.Message):
    """Обработка любого текстового сообщения (кроме команд)"""
    # Проверяем, не админ ли это
    if message.from_user.id in ADMIN_IDS:
        return
    
    # Сохраняем сообщение
    message_data = {
        "id": message.message_id,
        "user_id": message.from_user.id,
        "username": message.from_user.username or "нет username",
        "text": message.text,
        "timestamp": str(message.date)
    }
    save_pending(message_data)
    
    # Уведомляем админов
    for admin_id in ADMIN_IDS:
        try:
            # Создаём кнопку для ответа
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"✏️ Ответить @{message.from_user.username or message.from_user.id}",
                    callback_data=f"reply_{message.from_user.id}_{message.message_id}"
                )]
            ])
            
            await message.bot.send_message(
                admin_id,
                f"📩 *Новое сообщение в поддержку*\n\n"
                f"👤 *Пользователь:* @{message.from_user.username or 'нет'}\n"
                f"🆔 *ID:* `{message.from_user.id}`\n\n"
                f"💬 *Сообщение:*\n{message.text}",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Ошибка отправки админу: {e}")
    
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


@router.callback_query(lambda c: c.data.startswith("reply_"))
async def start_reply(callback: types.CallbackQuery, state: FSMContext):
    """Начать ответ пользователю (для админа)"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    parts = callback.data.split("_")
    user_id = int(parts[1])
    message_id = int(parts[2]) if len(parts) > 2 else None
    
    await state.update_data(reply_user_id=user_id, original_message_id=message_id)
    
    await callback.message.answer(
        f"✏️ *Введите ответ для пользователя* (ID: `{user_id}`)\n\n"
        f"Напишите сообщение, и оно будет отправлено.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_reply")]
        ])
    )
    await state.set_state(SupportState.waiting_for_reply)
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel_reply")
async def cancel_reply(callback: types.CallbackQuery, state: FSMContext):
    """Отмена ответа"""
    await state.clear()
    await callback.message.edit_text("✅ Ответ отменён")
    await callback.answer()


@router.message(SupportState.waiting_for_reply)
async def send_reply(message: types.Message, state: FSMContext):
    """Отправить ответ пользователю"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Доступ запрещён")
        await state.clear()
        return
    
    data = await state.get_data()
    user_id = data.get('reply_user_id')
    
    if not user_id:
        await message.answer("❌ Ошибка: пользователь не найден")
        await state.clear()
        return
    
    try:
        await message.bot.send_message(
            user_id,
            f"📞 *Ответ от поддержки MILF VPN:*\n\n{message.text}\n\n"
            f"✏️ Если остались вопросы, напишите снова.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📞 Написать в поддержку", callback_data="support")]
            ])
        )
        await message.answer(f"✅ Ответ отправлен пользователю `{user_id}`", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")
    
    await state.clear()


@router.message(Command("support_list"))
async def list_pending_messages(message: types.Message):
    """Список непрочитанных сообщений (админ-команда)"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Доступ запрещён")
        return
    
    pending = get_pending()
    
    if not pending:
        await message.answer("📭 *Нет непрочитанных сообщений*", parse_mode="Markdown")
        return
    
    text = f"📬 *Непрочитанные сообщения:* ({len(pending)})\n\n"
    for i, msg in enumerate(pending[-10:], 1):  # последние 10
        text += f"{i}. @{msg['username']}: {msg['text'][:50]}...\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить очередь", callback_data="clear_pending")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(lambda c: c.data == "clear_pending")
async def clear_pending_messages(callback: types.CallbackQuery):
    """Очистить очередь сообщений"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    clear_pending()
    await callback.message.edit_text("✅ Очередь сообщений очищена")
    await callback.answer()
