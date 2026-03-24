import asyncio
import logging
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database.session import init_db
from handlers import (
    start, main_menu, trial, instructions, subscription, profile, referral, admin, payments
)
from handlers.vpn import router as vpn_router
from handlers.feedback import router as feedback_router
from utils.scheduler import start_scheduler


async def health_check(request):
    """Health check для Render"""
    return web.Response(text="OK")


async def ping(request):
    """Простой ping для keep-alive"""
    return web.Response(text="pong")


async def start_http_server():
    """Запуск HTTP сервера для health check и keep-alive"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/ping', ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    print("✅ HTTP server started on port 10000")
    
    # Бесконечное ожидание с периодическим пингом самого себя
    while True:
        await asyncio.sleep(300)  # 5 минут
        # Делаем запрос к самому себе, чтобы держать процесс активным
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:10000/ping') as resp:
                    if resp.status == 200:
                        print("✅ Keep-alive ping successful")
        except Exception as e:
            print(f"⚠️ Keep-alive ping failed: {e}")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Starting MILF VPN Bot...")
    
    await init_db()
    print("✅ Database initialized")

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
        feedback_router,
    )
    print("✅ Routers registered")

    # Запускаем HTTP-сервер для health check
    asyncio.create_task(start_http_server())

    # Запускаем планировщик
    start_scheduler(bot)
    print("✅ Scheduler started")

    # Запускаем поллинг
    print("🤖 Bot started polling...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
