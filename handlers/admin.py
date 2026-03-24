import shlex
from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy import select, func, delete
from config import ADMIN_IDS
from database.session import AsyncSessionLocal
from database.models import Plan, Server, User, Subscription, Transaction, Trial, ReferralBonus
from database.crud import create_promo_code, get_all_promo_codes

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command('admin'), F.from_user.id.in_(ADMIN_IDS))
async def admin_panel(message: types.Message):
    await message.answer(
        "👑 *Админ-панель MILF VPN*\n\n"
        "/stat - статистика\n"
        "/add_plan \"Название\" дни цена_звёзды цена_рубли_копейки\n"
        "/del_plan <id> - удалить тариф\n"
        "/servers - список серверов\n"
        "/add_server - добавить сервер\n"
        "/clear_trial [user_id] - очистить пробный период пользователя\n"
        "/create_promo <дни> <макс_использований> [код] - создать промокод\n"
        "/list_promo - список промокодов",
        parse_mode="Markdown"
    )


@router.message(Command('add_plan'), F.from_user.id.in_(ADMIN_IDS))
async def add_plan(message: types.Message):
    """Формат: /add_plan "Название" дни цена_звёзды цена_рубли_копейки"""
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
        plan = Plan(
            name=name,
            duration_days=days,
            price_stars=stars,
            price_rub=rub,
            is_active=True
        )
        session.add(plan)
        await session.commit()
    
    await message.answer(f"✅ Тариф *{name}* добавлен\n📅 {days} дней | ⭐ {stars} | ₽ {rub/100}", parse_mode="Markdown")


@router.message(Command('del_plan'), F.from_user.id.in_(ADMIN_IDS))
async def delete_plan(message: types.Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Используйте: /del_plan <id_тарифа>")
        return
    
    try:
        plan_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    
    async with AsyncSessionLocal() as session:
        plan = await session.get(Plan, plan_id)
        if not plan:
            await message.answer(f"❌ Тариф с ID {plan_id} не найден")
            return
        
        plan.is_active = False
        await session.commit()
    
    await message.answer(f"✅ Тариф *{plan.name}* отключён (ID: {plan_id})", parse_mode="Markdown")


@router.message(Command('stat'), F.from_user.id.in_(ADMIN_IDS))
async def stats(message: types.Message):
    async with AsyncSessionLocal() as session:
        total_users = await session.execute(select(func.count()).select_from(User))
        active_subs = await session.execute(
            select(func.count()).select_from(Subscription).where(Subscription.is_active == True)
        )
        income_stars = await session.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.status == 'completed', 
                Transaction.currency == 'XTR'
            )
        )
        income_rub = await session.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.status == 'completed', 
                Transaction.currency == 'RUB'
            )
        )
        
        stars = income_stars.scalar() or 0
        rub = income_rub.scalar() or 0
        
        await message.answer(
            f"📊 *Статистика MILF VPN*\n\n"
            f"👥 Всего пользователей: {total_users.scalar() or 0}\n"
            f"✅ Активных подписок: {active_subs.scalar() or 0}\n"
            f"⭐ Доход (звёзды): {stars}\n"
            f"💰 Доход (рубли): {rub/100:.2f} ₽",
            parse_mode="Markdown"
        )


@router.message(Command('servers'), F.from_user.id.in_(ADMIN_IDS))
async def list_servers(message: types.Message):
    async with AsyncSessionLocal() as session:
        servers = await session.execute(select(Server))
        servers = servers.scalars().all()
        
        if not servers:
            await message.answer("📭 Нет добавленных серверов\nИспользуйте /add_server для добавления")
            return
        
        text = "🖥️ *Серверы:*\n\n"
        for s in servers:
            text += f"🆔 {s.id} | {s.name} | {s.location}\n"
            text += f"   📡 {s.host}\n"
            text += f"   👥 {s.current_clients}/{s.max_clients} клиентов\n\n"
        
        await message.answer(text, parse_mode="Markdown")


@router.message(Command('add_server'), F.from_user.id.in_(ADMIN_IDS))
async def add_server_command(message: types.Message):
    """Добавить сервер в БД"""
    async with AsyncSessionLocal() as session:
        # Проверяем, есть ли уже сервер с id=1
        result = await session.execute(select(Server).where(Server.id == 1))
        existing = result.scalar_one_or_none()
        
        if existing:
            await message.answer("✅ Сервер уже существует!\n\n"
                               f"ID: {existing.id}\n"
                               f"Имя: {existing.name}\n"
                               f"Хост: {existing.host}\n"
                               f"Локация: {existing.location}")
            return
        
        server = Server(
            id=1,
            name='Main Server',
            host='87.242.86.245',
            api_url='http://87.242.86.245:49828/bJGC3webPGJwCrGw5e',
            api_username='zmfJGlol8h',
            api_password='qZPX8SHumS',
            location='Frankfurt',
            max_clients=100,
            current_clients=0
        )
        session.add(server)
        await session.commit()
        
        await message.answer(
            "✅ *Сервер успешно добавлен!*\n\n"
            "🆔 ID: 1\n"
            "📛 Имя: Main Server\n"
            "📍 Локация: Frankfurt\n"
            "📡 Хост: 87.242.86.245\n"
            "👥 Максимум клиентов: 100",
            parse_mode="Markdown"
        )


@router.message(Command('clear_trial'), F.from_user.id.in_(ADMIN_IDS))
async def clear_trial(message: types.Message):
    """Очистить пробный период пользователя: /clear_trial [user_id]"""
    args = message.text.split()
    
    # Если указан user_id, используем его, иначе свой
    if len(args) > 1:
        try:
            user_id = int(args[1])
        except ValueError:
            await message.answer("❌ ID пользователя должен быть числом")
            return
    else:
        user_id = message.from_user.id
    
    async with AsyncSessionLocal() as session:
        # Удаляем подписки с plan_id=None (пробные)
        result_sub = await session.execute(
            delete(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.plan_id == None
            )
        )
        
        # Удаляем записи в trials
        result_trial = await session.execute(
            delete(Trial).where(Trial.user_id == user_id)
        )
        
        # Сбрасываем флаг trial_used у пользователя
        user = await session.get(User, user_id)
        if user:
            user.trial_used = False
            user.trial_end_date = None
        
        await session.commit()
        
        deleted_subs = result_sub.rowcount
        deleted_trials = result_trial.rowcount
        
        await message.answer(
            f"✅ *Пробный период очищен для пользователя* `{user_id}`\n\n"
            f"🗑 Удалено подписок: {deleted_subs}\n"
            f"🗑 Удалено trial-записей: {deleted_trials}\n\n"
            f"Пользователь может активировать пробный период заново.",
            parse_mode="Markdown"
        )


@router.message(Command('create_promo'), F.from_user.id.in_(ADMIN_IDS))
async def create_promo(message: types.Message):
    """Создать промокод: /create_promo дни макс_использований [код]"""
    args = message.text.split()
    
    if len(args) < 3:
        await message.answer(
            "📝 *Формат:*\n"
            "/create_promo <дни> <макс_использований> [код]\n\n"
            "Примеры:\n"
            "/create_promo 30 1 — создаст случайный код на 30 дней, 1 использование\n"
            "/create_promo 7 10 FREETEST — создаст код FREETEST на 7 дней, 10 использований",
            parse_mode="Markdown"
        )
        return
    
    try:
        days = int(args[1])
        max_uses = int(args[2])
    except ValueError:
        await message.answer("❌ Дни и количество использований должны быть числами")
        return
    
    code = args[3].upper() if len(args) > 3 else None
    
    async with AsyncSessionLocal() as session:
        import random
        import string
        
        if not code:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        promo = await create_promo_code(
            session=session,
            code=code,
            days=days,
            max_uses=max_uses,
            created_by=message.from_user.id
        )
        
        await message.answer(
            f"🎁 *Промокод создан!*\n\n"
            f"🔑 *Код:* `{promo.code}`\n"
            f"📅 *Дней:* {promo.days}\n"
            f"👥 *Использований:* {promo.max_uses}\n\n"
            f"Ссылка для активации:\n"
            f"`/activate {promo.code}`",
            parse_mode="Markdown"
        )


@router.message(Command('list_promo'), F.from_user.id.in_(ADMIN_IDS))
async def list_promo(message: types.Message):
    """Список всех промокодов"""
    async with AsyncSessionLocal() as session:
        promos = await get_all_promo_codes(session)
        
        if not promos:
            await message.answer("📭 Нет созданных промокодов")
            return
        
        text = "🎁 *Список промокодов:*\n\n"
        for promo in promos[:20]:
            status = "✅" if promo.is_active and promo.used_count < promo.max_uses else "❌"
            text += f"{status} `{promo.code}` — {promo.days} дн. (исп. {promo.used_count}/{promo.max_uses})\n"
        
        await message.answer(text, parse_mode="Markdown")
