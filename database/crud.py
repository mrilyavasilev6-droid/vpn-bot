from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, Plan, Subscription, Server, Transaction, ReferralBonus
import datetime

async def get_user(session: AsyncSession, user_id: int):
    result = await session.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()

async def create_user(session: AsyncSession, user_id: int, username: str, referrer_id: int = None):
    user = User(user_id=user_id, username=username, referral_by=referrer_id)
    session.add(user)
    await session.commit()
    return user

async def get_active_plan(session: AsyncSession, plan_id: int):
    result = await session.execute(select(Plan).where(Plan.id == plan_id, Plan.is_active == True))
    return result.scalar_one_or_none()

async def get_all_plans(session: AsyncSession):
    result = await session.execute(select(Plan).where(Plan.is_active == True))
    return result.scalars().all()

async def get_least_loaded_server(session: AsyncSession):
    result = await session.execute(select(Server).where(Server.max_clients > Server.current_clients))
    servers = result.scalars().all()
    if not servers:
        return None
    return min(servers, key=lambda s: s.current_clients / s.max_clients if s.max_clients else 0)

async def create_subscription(session: AsyncSession, user_id: int, plan_id: int, client_id: str, server_id: int, end_date: datetime.datetime):
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

async def add_transaction(session: AsyncSession, user_id: int, amount: int, currency: str, method: str, payload: str = None):
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