from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy import text
from config import ADMIN_IDS
from database.session import AsyncSessionLocal
from database.models import Plan, Server
from sqlalchemy import select, func

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command('admin'), F.from_user.id.in_(ADMIN_IDS))
async def admin_panel(message: types.Message):
    await message.answer(
        "👑 Админ-панель:\n"
        "/stat - статистика\n"
        "/add_plan \"Название\" дни цена_звёзды цена_рубли_копейки\n"
        "/servers - список серверов\n"
        "/migrate - добавить недостающие колонки в БД\n"
        "/add_tariffs - добавить стандартные тарифы"
    )

@router.message(Command('stat'), F.from_user.id.in_(ADMIN_IDS))
async def stats(message: types.Message):
    async with AsyncSessionLocal() as session:
        total_users = await session.execute(select(func.count()).select_from(select(User)))
        active_subs = await session.execute(select(func.count()).select_from(Subscription).where(Subscription.is_active == True))
        income = await session.execute(select(func.sum(Transaction.amount)).where(Transaction.status == 'completed', Transaction.currency == 'RUB'))
        await message.answer(
            f"📊 Статистика:\n"
            f"👥 Всего пользователей: {total_users.scalar()}\n"
            f"✅ Активных подписок: {active_subs.scalar()}\n"
            f"💰 Доход (руб): {income.scalar()/100 if income.scalar() else 0}"
        )

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
    await message.answer(f"✅ Тариф {name} добавлен")

@router.message(Command('add_tariffs'), F.from_user.id.in_(ADMIN_IDS))
async def add_default_tariffs(message: types.Message):
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(Plan))
        if existing.scalars().first():
            await message.answer("⚠️ Тарифы уже есть в базе. Если нужно обновить, удалите их вручную.")
            return
        plans = [
            Plan(name='1 месяц', duration_days=30, price_stars=75, price_rub=15000, description='30 дней доступа, 1 устройство'),
            Plan(name='3 месяца', duration_days=90, price_stars=200, price_rub=45000, description='90 дней доступа, 1 устройство'),
            Plan(name='12 месяцев', duration_days=365, price_stars=750, price_rub=150000, description='365 дней доступа, 1 устройство')
        ]
        session.add_all(plans)
        await session.commit()
    await message.answer("✅ Стандартные тарифы добавлены!")

@router.message(Command('migrate'), F.from_user.id.in_(ADMIN_IDS))
async def migrate_db(message: types.Message):
    """Добавляет недостающие колонки в таблицу users"""
    async with AsyncSessionLocal() as session:
        results = []
        try:
            await session.execute(text("ALTER TABLE users ADD COLUMN balance INTEGER DEFAULT 0"))
            results.append("✅ Колонка balance добавлена")
        except Exception as e:
            if "already exists" in str(e):
                results.append("ℹ️ Колонка balance уже есть")
            else:
                results.append(f"❌ balance: {e}")
        try:
            await session.execute(text("ALTER TABLE users ADD COLUMN auto_renew BOOLEAN DEFAULT FALSE"))
            results.append("✅ Колонка auto_renew добавлена")
        except Exception as e:
            if "already exists" in str(e):
                results.append("ℹ️ Колонка auto_renew уже есть")
            else:
                results.append(f"❌ auto_renew: {e}")
        try:
            await session.execute(text("ALTER TABLE users ADD COLUMN trial_used BOOLEAN DEFAULT FALSE"))
            results.append("✅ Колонка trial_used добавлена")
        except Exception as e:
            if "already exists" in str(e):
                results.append("ℹ️ Колонка trial_used уже есть")
            else:
                results.append(f"❌ trial_used: {e}")
        try:
            await session.execute(text("ALTER TABLE users ADD COLUMN trial_end_date TIMESTAMP"))
            results.append("✅ Колонка trial_end_date добавлена")
        except Exception as e:
            if "already exists" in str(e):
                results.append("ℹ️ Колонка trial_end_date уже есть")
            else:
                results.append(f"❌ trial_end_date: {e}")
        await session.commit()
    await message.answer("\n".join(results))

@router.message(Command('servers'), F.from_user.id.in_(ADMIN_IDS))
async def list_servers(message: types.Message):
    async with AsyncSessionLocal() as session:
        servers = await session.execute(select(Server))
        servers = servers.scalars().all()
        if not servers:
            await message.answer("Нет добавленных серверов.")
            return
        text = "🖥 Серверы:\n"
        for s in servers:
            text += f"🔹 {s.name} ({s.location}) – клиентов: {s.current_clients}/{s.max_clients}\n"
        await message.answer(text)
