from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.models import Subscription, Server, User
from vpn.xui import XUIClient
import logging

scheduler = AsyncIOScheduler()

async def check_expired_subscriptions():
    async with AsyncSessionLocal() as session:
        now = datetime.now()
        expired = await session.execute(
            select(Subscription).where(Subscription.is_active == True, Subscription.end_date <= now)
        )
        for sub in expired.scalars().all():
            server = await session.get(Server, sub.server_id)
            if server:
                xui = XUIClient(server.api_url, server.api_username, server.api_password)
                try:
                    await xui.delete_client(sub.client_id)
                    server.current_clients -= 1
                    sub.is_active = False
                except Exception as e:
                    logging.error(f"Ошибка удаления клиента {sub.client_id}: {e}")
            await session.commit()

async def notify_expiring(bot):
    async with AsyncSessionLocal() as session:
        now = datetime.now()
        for days in [3, 2, 1]:
            target = now + timedelta(days=days)
            subs = await session.execute(
                select(Subscription, User)
                .join(User, Subscription.user_id == User.user_id)
                .where(Subscription.is_active == True,
                       Subscription.end_date.between(target, target + timedelta(days=1)))
            )
            for sub, user in subs:
                await bot.send_message(
                    user.user_id,
                    f"Ваша подписка истекает через {days} дня/дней. Продлите её, чтобы не потерять доступ."
                )

def start_scheduler(bot):
    scheduler.add_job(check_expired_subscriptions, CronTrigger(hour=0, minute=0))
    scheduler.add_job(lambda: notify_expiring(bot), CronTrigger(hour=9, minute=0))
    scheduler.start()
