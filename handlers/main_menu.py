from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
import os

router = Router()


def get_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 3 дня бесплатно", callback_data="trial_start")],
        [InlineKeyboardButton(text="💎 Выбрать тариф", callback_data="subscription")],
        [InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="referral")],
        [InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions")],
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")],
        [InlineKeyboardButton(text="❓ Поддержка", callback_data="support")]
    ])


async def show_main_menu(message: types.Message):
    text = (
        "### 💎 Что умеет MILF VPN?\n\n"
        "**Опыт, которому можно доверять.**\n"
        "Быстрый и стабильный VPN для взрослых задач:\n\n"
        "- 📞 Звонки в любых мессенджерах\n"
        "- 🤖 ChatGPT, Midjourney, нейросети\n"
        "- 🎬 YouTube, Netflix, Twitch — без буфера\n"
        "- 🌍 Обход любых блокировок\n"
        "- 🔒 Полная конфиденциальность\n\n"
        "✨ *Оформи пробный период — 3 дня в подарок. Оцени скорость и надёжность, прежде чем выбрать тариф.*"
    )
    
    # Путь к картинке
    photo_path = os.path.join("assets", "banner-vpn-bot.png")
    
    try:
        photo = FSInputFile(photo_path)
        await message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        # Если ошибка — отправляем без картинки
        await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
        print(f"Error loading image: {e}")


@router.callback_query(lambda c: c.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery):
    await show_main_menu(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data == "support")
async def support(callback: types.CallbackQuery):
    await callback.message.answer(
        "📞 *Поддержка MILF VPN*\n\n"
        "По всем вопросам обращайтесь:\n"
        "✉️ @support_username\n"
        "📧 support@milfvpn.com\n\n"
        "Ответим в течение 24 часов. Всегда на связи.",
        parse_mode="Markdown"
    )
    await callback.answer()
