from aiogram import Router, types, F
from aiogram.filters import Command
from config import ADMIN_IDS
from database.session import AsyncSessionLocal
from database.models import Plan, Server
from sqlalchemy import select

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command('admin'), F.from_user.id.in_(ADMIN_IDS))
async def admin_panel(message: types.Message):
    await message.answer("Админ-панель:\n"
                         "/stat - статистика\n"
                         "/add_plan \"Название\" дней цена_звёзды цена_рубли_копейки\n"
                         "/servers - список серверов\n"
                         "/add_server - добавить сервер (пока вручную)")

@router.message(Command('add_plan'), F.from_user.id.in_(ADMIN_IDS))
async def add_plan(message: types.Message):
    args = message.text.split(maxsplit=4)
    if len(args) < 5:
        await message.answer("Формат: /add_plan \"Название\" дни цена_звёзды цена_рубли_копейки")
        return
    name = args[1].strip('"')
    days = int(args[2])
    stars = int(args[3])
    rub = int(args[4])
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
@router.message(Command('add_plans'), F.from_user.id.in_(ADMIN_IDS))
async def add_default_plans(message: types.Message):
    from database.models import Plan
    async with AsyncSessionLocal() as session:
        plans = [
            Plan(name='1 месяц', duration_days=30, price_stars=75, price_rub=15000, description='30 дней доступа, 1 устройство'),
            Plan(name='3 месяца', duration_days=90, price_stars=200, price_rub=45000, description='90 дней доступа, 1 устройство'),
            Plan(name='12 месяцев', duration_days=365, price_stars=750, price_rub=150000, description='365 дней доступа, 1 устройство')
        ]
        session.add_all(plans)
        await session.commit()
    await message.answer("✅ Тарифы добавлены!")
