import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database.session import engine
from database.models import Base
from handlers import start, buy, profile, admin, payments
from utils.scheduler import start_scheduler

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def health_check(request):
    return web.Response(text="OK")

async def start_http_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    # Бесконечное ожидание, чтобы задача не завершалась
    await asyncio.Event().wait()

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_routers(start.router, buy.router, profile.router, admin.router, payments.router)

    # Запускаем HTTP‑сервер для health check (Render будет видеть порт)
    asyncio.create_task(start_http_server())

    # Запускаем планировщик, передавая бота для отправки уведомлений
    start_scheduler(bot)

    # Запускаем бота в режиме long polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
