from aiogram import Router, types
from aiogram.filters import CommandStart
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.models import User
from handlers.main_menu import show_main_menu

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username

    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.user_id == user_id))
        user = user.scalar_one_or_none()

        if not user:
            args = message.text.split()
            referrer_id = None
            if len(args) > 1 and args[1].startswith('ref_'):
                try:
                    referrer_id = int(args[1][4:])
                except ValueError:
                    pass
            user = User(user_id=user_id, username=username, referral_by=referrer_id)
            session.add(user)
            await session.commit()

    await show_main_menu(message)
