import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database.session import init_db
from handlers import (
    start, main_menu, trial, instructions, subscription, profile, referral, admin, payments
)
from handlers.vpn import router as vpn_router
from handlers.feedback import router as feedback_router  # ← ДОБАВИТЬ
from utils.scheduler import start_scheduler


async def health_check(request):
    return web.Response(text="OK")


async def start_http_server():
    """Запуск HTTP сервера для health check"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    while True:
        await asyncio.sleep(3600)


async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_routers(
        start.router,
        main_menu.router,
        trial.router,
        instructions.router,
        subscription.router,
        profile.router,
        referral.router,
        admin.router,
        payments.router,
        vpn_router,
        feedback_router,  # ← ДОБАВИТЬ СЮДА
    )

    # Запускаем HTTP-сервер для health check
    asyncio.create_task(start_http_server())

    # Запускаем планировщик
    start_scheduler(bot)

    # Запускаем поллинг
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
