from aiogram import Router, types
from aiogram.filters import CommandStart
from database.session import get_session
from database.crud import get_user, create_user

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""

    async with get_session() as session:
        user = await get_user(session, user_id)
        if not user:
            args = message.text.split()
            referrer_id = None
            if len(args) > 1 and args[1].startswith('ref_'):
                try:
                    referrer_id = int(args[1][4:])
                except:
                    pass
            user = await create_user(session, user_id, username, referrer_id)

    await message.answer(
        "Добро пожаловать в VPN-бот! 🚀\n"
        "Используйте /buy для покупки подписки.\n"
        "/profile — личный кабинет."
    )