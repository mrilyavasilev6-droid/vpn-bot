import shlex
from aiogram import Router, types, F
from aiogram.filters import Command
from config import ADMIN_IDS
from database.session import AsyncSessionLocal
from database.models import Plan, Server
from sqlalchemy import select, func

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command('admin'), F.from_user.id.in_(ADMIN_IDS))
async def admin_panel(message: types.Message):
    await message.answer("Админ-панель:\n"
                         "/stat - статистика\n"
                         "/add_plan \"Название\" дни цена_звёзды цена_рубли_копейки\n"
                         "/servers - список серверов\n"
                         "/add_server - добавить сервер (пока вручную)")

@router.message(Command('add_plan'), F.from_user.id.in_(ADMIN_IDS))
async def add_plan(message: types.Message):
    # Формат: /add_plan "Название" дни цена_звезды цена_рубли_копейки
    try:
        args = shlex.split(message.text)
    except ValueError:
        await message.answer("Ошибка: неправильный формат кавычек. Используйте двойные кавычки для названия.")
        return
    if len(args) != 5:
        await message.answer("Формат: /add_plan \"Название\" дни цена_звёзды цена_рубли_копейки")
        return
    name = args[1]
    try:
        days = int(args[2])
        stars = int(args[3])
        rub = int(args[4])
    except ValueError:
        await message.answer("Ошибка: дни, цена в звёздах и рублях должны быть числами.")
        return
    async with AsyncSessionLocal() as session:
        plan = Plan(name=name, duration_days=days, price_stars=stars, price_rub=rub)
        session.add(plan)
        await session.commit()
    await message.answer(f"Тариф {name} добавлен")

@router.message(Command('stat'), F.from_user.id.in_(ADMIN_IDS))
async def stats(message: types.Message):
    async with AsyncSessionLocal() as session:
        from database.models import User, Subscription, Transaction
        total_users = await session.execute(select(func.count()).select_from(User))
        active_subs = await session.execute(select(func.count()).select_from(Subscription).where(Subscription.is_active == True))
        income = await session.execute(select(func.sum(Transaction.amount)).where(Transaction.status == 'completed', Transaction.currency == 'RUB'))
        await message.answer(
            f"Всего пользователей: {total_users.scalar()}\n"
            f"Активных подписок: {active_subs.scalar()}\n"
            f"Доход (руб): {income.scalar()/100 if income.scalar() else 0}"
        )
