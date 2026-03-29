from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.models import Subscription, Server, User
from config import MOCK_MODE
import logging

scheduler = AsyncIOScheduler()
logger = logging.getLogger(__name__)


async def check_expired_subscriptions():
    """Деактивирует истекшие подписки в БД."""
    if MOCK_MODE:
        logger.info("MOCK_MODE: skip expired subscriptions check")
        return
    
    async with AsyncSessionLocal() as session:
        now = datetime.now()
        expired = await session.execute(
            select(Subscription).where(
                Subscription.is_active == True,
                Subscription.end_date <= now
            )
        )
        
        expired_list = expired.scalars().all()
        
        if not expired_list:
            return
        
        logger.info(f"Found {len(expired_list)} expired subscriptions to process")
        
        for sub in expired_list:
            try:
                # Деактивируем подписку в БД
                sub.is_active = False
                logger.info(f"✅ Deactivated expired subscription: {sub.client_id} (user {sub.user_id})")
            except Exception as e:
                logger.error(f"❌ Error deactivating subscription {sub.client_id}: {e}")
        
        await session.commit()


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
                .where(
                    Subscription.is_active == True,
                    Subscription.end_date >= target,
                    Subscription.end_date < target_end
                )
            )
            
            for sub, user in subs:
                # Определяем тип подписки
                if sub.plan_id:
                    sub_type = "платная подписка"
                else:
                    sub_type = "пробный период"
                
                end_date_str = sub.end_date.strftime('%d.%m.%Y %H:%M')
                
                try:
                    await bot.send_message(
                        user.user_id,
                        f"⚠️ *Важная информация о подписке MILF VPN*\n\n"
                        f"Ваш{sub_type} истекает через {days} дня/дней.\n\n"
                        f"📅 *Дата окончания:* {end_date_str} МСК\n\n"
                        f"Чтобы не потерять доступ, продлите подписку в разделе «Выбрать тариф».\n\n"
                        f"✨ После продления подписка продолжит работать автоматически",
                        parse_mode="Markdown"
                    )
                    logger.info(f"Expiration notification sent to user {user.user_id} ({days} days left)")
                except Exception as e:
                    logger.error(f"Error notifying user {user.user_id}: {e}")


async def daily_stats(bot):
    """Ежедневная статистика для админов (опционально)"""
    from config import ADMIN_IDS
    from database.models import User, Subscription, Transaction
    from sqlalchemy import func
    
    async with AsyncSessionLocal() as session:
        total_users = await session.execute(select(func.count()).select_from(User))
        active_subs = await session.execute(
            select(func.count()).select_from(Subscription).where(Subscription.is_active == True)
        )
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_income = await session.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.status == 'completed',
                Transaction.created_at >= today_start
            )
        )
        
        total_users = total_users.scalar() or 0
        active_subs = active_subs.scalar() or 0
        today_income = today_income.scalar() or 0
        
        stats_text = (
            f"📊 *Ежедневная статистика MILF VPN*\n\n"
            f"📅 *Дата:* {datetime.now().strftime('%d.%m.%Y')}\n\n"
            f"👥 *Всего пользователей:* {total_users}\n"
            f"✅ *Активных подписок:* {active_subs}\n"
            f"💰 *Доход за сегодня:* {today_income/100:.2f} ₽\n\n"
            f"🌍 *Серверы:* Панель Marzban\n"
            f"🔗 *Панель управления:* https://vpn.olin.mooo.com/dashboard/"
        )
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, stats_text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Error sending stats to admin {admin_id}: {e}")


def start_scheduler(bot):
    """Запуск планировщика"""
    # Проверка истекших подписок каждый день в 00:00
    scheduler.add_job(check_expired_subscriptions, CronTrigger(hour=0, minute=0))
    
    # Уведомления об истечении подписки каждый день в 09:00
    scheduler.add_job(lambda: notify_expiring(bot), CronTrigger(hour=9, minute=0))
    
    # Ежедневная статистика для админов в 23:59
    scheduler.add_job(lambda: daily_stats(bot), CronTrigger(hour=23, minute=59))
    
    scheduler.start()
    logger.info("✅ Scheduler started")
