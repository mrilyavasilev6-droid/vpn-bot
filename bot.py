import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database.session import engine
from database.models import Base
from handlers import start, buy, profile, admin, payments
from utils.scheduler import start_scheduler

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_routers(start.router, buy.router, profile.router, admin.router, payments.router)

    # Запускаем планировщик, передавая бота для отправки уведомлений
    start_scheduler(bot)

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())