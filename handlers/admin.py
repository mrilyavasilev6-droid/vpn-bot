from aiogram import Router, types, F
from aiogram.filters import Command
from config import ADMIN_IDS
from database.session import get_session
from database.models import Plan, Server
from sqlalchemy import select

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command('admin'), F.from_user.id.in_(ADMIN_IDS))
async def admin_panel(message: types.Message):
    await message.answer("Админ-панель:\n/stat - статистика\n/add_plan - добавить тариф\n/servers - управление серверами")

@router.message(Command('add_plan'), F.from_user.id.in_(ADMIN_IDS))
async def add_plan(message: types.Message):
    # /add_plan "Премиум" 30 500 1500
    args = message.text.split(maxsplit=4)
    if len(args) < 5:
        await message.answer("Формат: /add_plan \"Название\" дней цена_звезды цена_рубли_в_копейках")
        return
    name = args[1].strip('"')
    duration = int(args[2])
    price_stars = int(args[3])
    price_rub = int(args[4])
    async with get_session() as session:
        plan = Plan(name=name, duration_days=duration, price_stars=price_stars, price_rub=price_rub)
        session.add(plan)
        await session.commit()
    await message.answer(f"Тариф {name} добавлен")