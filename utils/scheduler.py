from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.models import Subscription, Server, User
from vpn.xui import XUIClient
from config import XUI_HOST, XUI_USERNAME, XUI_PASSWORD, MOCK_MODE
import logging

scheduler = AsyncIOScheduler()


async def check_expired_subscriptions():
    """Удаляет истекшие подписки и отключает клиентов на серверах."""
    if MOCK_MODE:
        logging.info("MOCK_MODE: skip expired subscriptions check")
        return
    
    async with AsyncSessionLocal() as session:
        now = datetime.now()
        expired = await session.execute(
            select(Subscription).where(Subscription.is_active == True, Subscription.end_date <= now)
        )
        
        xui = XUIClient(XUI_HOST, XUI_USERNAME, XUI_PASSWORD)
        
        for sub in expired.scalars().all():
            try:
                await xui.delete_client(sub.client_id)
                sub.is_active = False
                logging.info(f"Deleted expired client: {sub.client_id}")
            except Exception as e:
                logging.error(f"Ошибка удаления клиента {sub.client_id}: {e}")
            
            await session.commit()
        
        await xui.close()


async def notify_expiring(bot):
    """Уведомляет пользователей за 3, 2 и 1 день до окончания подписки."""
    async with AsyncSessionLocal() as session:
        now = datetime.now()
        for days in [3, 2, 1]:
            target = now + timedelta(days=days)
            target_end = target + timedelta(days=1)
            
            subs = await session.execute(
                select(Subscription, User)
                .join(User, Subscription.user_id == User.user_id)
                .where(Subscription.is_active == True,
                       Subscription.end_date >= target,
                       Subscription.end_date < target_end)
            )
            
            for sub, user in subs:
                try:
                    await bot.send_message(
                        user.user_id,
                        f"⚠️ *Ваша подписка истекает через {days} дня/дней!*\n\n"
                        f"Продлите её, чтобы не потерять доступ к VPN.\n"
                        f"Используйте /buy для продления.",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logging.error(f"Error notifying user {user.user_id}: {e}")


def start_scheduler(bot):
    scheduler.add_job(check_expired_subscriptions, CronTrigger(hour=0, minute=0))
    scheduler.add_job(lambda: notify_expiring(bot), CronTrigger(hour=9, minute=0))
    scheduler.start()
    logging.info("Scheduler started")
