from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy import text
from config import ADMIN_IDS
from database.session import AsyncSessionLocal
from database.models import Plan, Server, User
from sqlalchemy import select, func

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command('admin'), F.from_user.id.in_(ADMIN_IDS))
async def admin_panel(message: types.Message):
    await message.answer(
        "Админ-панель:\n"
        "/stat - статистика\n"
        "/add_plan \"Название\" дней цена_звёзды цена_рубли_копейки\n"
        "/servers - список серверов\n"
        "/migrate - добавить недостающие колонки в таблицу users"
    )

@router.message(Command('migrate'), F.from_user.id.in_(ADMIN_IDS))
async def migrate_db(message: types.Message):
    """Добавляет недостающие колонки в таблицу users"""
    async with AsyncSessionLocal() as session:
        results = []
        try:
            await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS balance INTEGER DEFAULT 0"))
            results.append("✅ balance добавлен")
        except Exception as e:
            results.append(f"balance: {e}")

        try:
            await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS auto_renew BOOLEAN DEFAULT FALSE"))
            results.append("✅ auto_renew добавлен")
        except Exception as e:
            results.append(f"auto_renew: {e}")

        try:
            await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_used BOOLEAN DEFAULT FALSE"))
            results.append("✅ trial_used добавлен")
        except Exception as e:
            results.append(f"trial_used: {e}")

        try:
            await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_end_date TIMESTAMP"))
            results.append("✅ trial_end_date добавлен")
        except Exception as e:
            results.append(f"trial_end_date: {e}")

        await session.commit()

    await message.answer("\n".join(results))

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
        total_users = await session.execute(select(func.count()).select_from(User))
        active_subs = await session.execute(select(func.count()).select_from(Subscription).where(Subscription.is_active == True))
        income = await session.execute(select(func.sum(Transaction.amount)).where(Transaction.status == 'completed', Transaction.currency == 'RUB'))
        await message.answer(
            f"Всего пользователей: {total_users.scalar()}\n"
            f"Активных подписок: {active_subs.scalar()}\n"
            f"Доход (руб): {income.scalar()/100 if income.scalar() else 0}"
        )
