from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, Plan, Subscription, Server, Transaction, ReferralBonus, Trial
import datetime


async def get_user(session: AsyncSession, user_id: int):
    """Получить пользователя по ID"""
    result = await session.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user_id: int, username: str, referrer_id: int = None):
    """Создать нового пользователя"""
    user = User(user_id=user_id, username=username, referral_by=referrer_id)
    session.add(user)
    await session.commit()
    return user


async def get_plan(session: AsyncSession, plan_id: int):
    """Получить тариф по ID"""
    result = await session.execute(select(Plan).where(Plan.id == plan_id, Plan.is_active == True))
    return result.scalar_one_or_none()


async def get_all_active_plans(session: AsyncSession):
    """Получить все активные тарифы"""
    result = await session.execute(select(Plan).where(Plan.is_active == True))
    return result.scalars().all()


async def get_least_loaded_server(session: AsyncSession):
    """Получить наименее загруженный сервер"""
    result = await session.execute(
        select(Server).where(Server.max_clients > Server.current_clients)
    )
    servers = result.scalars().all()
    if not servers:
        return None
    return min(servers, key=lambda s: s.current_clients / s.max_clients if s.max_clients else 0)


async def get_user_active_subscription(session: AsyncSession, user_id: int):
    """Получить активную платную подписку пользователя"""
    now = datetime.datetime.now()
    result = await session.execute(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.is_active == True,
            Subscription.end_date > now,
            Subscription.plan_id != None  # только платные подписки
        )
    )
    return result.scalar_one_or_none()


async def get_user_any_active_subscription(session: AsyncSession, user_id: int):
    """Получить любую активную подписку (платную или пробную)"""
    now = datetime.datetime.now()
    result = await session.execute(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.is_active == True,
            Subscription.end_date > now
        )
    )
    return result.scalar_one_or_none()


async def add_subscription(
    session: AsyncSession, 
    user_id: int, 
    plan_id: int, 
    client_id: str, 
    server_id: int, 
    end_date: datetime.datetime
):
    """Добавить подписку"""
    sub = Subscription(
        user_id=user_id,
        plan_id=plan_id,
        client_id=client_id,
        server_id=server_id,
        end_date=end_date,
        is_active=True
    )
    session.add(sub)
    await session.commit()
    return sub


async def add_trial_subscription(
    session: AsyncSession,
    user_id: int,
    client_id: str,
    end_date: datetime.datetime
):
    """Добавить пробную подписку (без plan_id)"""
    sub = Subscription(
        user_id=user_id,
        plan_id=None,
        client_id=client_id,
        server_id=1,
        end_date=end_date,
        is_active=True
    )
    session.add(sub)
    await session.commit()
    return sub


async def deactivate_subscription(session: AsyncSession, subscription_id: int):
    """Деактивировать подписку"""
    await session.execute(
        update(Subscription)
        .where(Subscription.id == subscription_id)
        .values(is_active=False)
    )
    await session.commit()


async def add_transaction(
    session: AsyncSession, 
    user_id: int, 
    amount: int, 
    currency: str, 
    method: str, 
    payload: str = None
):
    """Добавить транзакцию"""
    tx = Transaction(
        user_id=user_id,
        amount=amount,
        currency=currency,
        payment_method=method,
        status='completed',
        telegram_payload=payload
    )
    session.add(tx)
    await session.commit()
    return tx


async def update_user_balance(session: AsyncSession, user_id: int, amount: int):
    """Обновить баланс пользователя"""
    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(balance=User.balance + amount)
    )
    await session.commit()


async def add_trial(session: AsyncSession, user_id: int, days: int = 3):
    """Добавить триальную запись"""
    end_date = datetime.datetime.now() + datetime.timedelta(days=days)
    trial = Trial(
        user_id=user_id,
        end_date=end_date,
        is_active=True
    )
    session.add(trial)
    await session.commit()
    await session.refresh(trial)
    return trial


async def get_active_trial(session: AsyncSession, user_id: int):
    """Получить активную триальную подписку"""
    now = datetime.datetime.now()
    result = await session.execute(
        select(Trial)
        .where(
            Trial.user_id == user_id,
            Trial.is_active == True,
            Trial.end_date > now
        )
    )
    return result.scalar_one_or_none()


async def mark_trial_used(session: AsyncSession, user_id: int):
    """Отметить, что пользователь использовал триал"""
    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(trial_used=True)
    )
    await session.commit()


# ============ Промокоды (если понадобятся позже) ============

async def create_promo_code(session: AsyncSession, code: str, days: int, max_uses: int = 1, created_by: int = None, expires_at: datetime.datetime = None):
    """Создать промокод"""
    from .models import PromoCode
    promo = PromoCode(
        code=code.upper(),
        days=days,
        max_uses=max_uses,
        created_by=created_by,
        expires_at=expires_at
    )
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return promo


async def get_promo_code(session: AsyncSession, code: str):
    """Получить промокод по коду"""
    from .models import PromoCode
    now = datetime.datetime.now()
    result = await session.execute(
        select(PromoCode).where(
            PromoCode.code == code.upper(),
            PromoCode.is_active == True,
            PromoCode.used_count < PromoCode.max_uses,
            (PromoCode.expires_at == None) | (PromoCode.expires_at > now)
        )
    )
    return result.scalar_one_or_none()


async def use_promo_code(session: AsyncSession, promo_id: int, user_id: int) -> bool:
    """Использовать промокод"""
    from .models import PromoCode, PromoCodeUsage
    # Проверяем, не использовал ли пользователь уже этот промокод
    result = await session.execute(
        select(PromoCodeUsage).where(
            PromoCodeUsage.promo_id == promo_id,
            PromoCodeUsage.user_id == user_id
        )
    )
    if result.scalar_one_or_none():
        return False
    
    # Записываем использование
    usage = PromoCodeUsage(promo_id=promo_id, user_id=user_id)
    session.add(usage)
    
    # Увеличиваем счётчик
    promo = await session.get(PromoCode, promo_id)
    promo.used_count += 1
    
    await session.commit()
    return True


async def get_all_promo_codes(session: AsyncSession):
    """Получить все промокоды"""
    from .models import PromoCode
    result = await session.execute(select(PromoCode).order_by(PromoCode.created_at.desc()))
    return result.scalars().all()
