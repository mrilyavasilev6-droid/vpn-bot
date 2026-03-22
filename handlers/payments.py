from aiogram import Router, types
from aiogram.types import LabeledPrice, PreCheckoutQuery
from config import PROVIDER_TOKEN
from database.session import get_session
from database.crud import get_active_plan, get_least_loaded_server, create_subscription, add_transaction
from vpn.xui import XUIClient
import datetime

router = Router()

# Обработчик оплаты через Telegram Stars
@router.callback_query(lambda c: c.data.startswith('pay_stars_'))
async def pay_with_stars(callback: types.CallbackQuery):
    plan_id = int(callback.data.split('_')[2])
    async with get_session() as session:
        plan = await get_active_plan(session, plan_id)
        if not plan:
            await callback.answer("Тариф не найден")
            return

    await callback.message.answer_invoice(
        title=plan.name,
        description=plan.description or f"VPN подписка на {plan.duration_days} дней",
        payload=f"plan_{plan_id}_{callback.from_user.id}",
        provider_token="",  # для Stars пусто
        currency="XTR",
        prices=[LabeledPrice(label=plan.name, amount=plan.price_stars)],
        start_parameter="vpn_subscription"
    )
    await callback.answer()

# Обработчик оплаты через ЮKassa
@router.callback_query(lambda c: c.data.startswith('pay_card_'))
async def pay_with_card(callback: types.CallbackQuery):
    plan_id = int(callback.data.split('_')[2])
    async with get_session() as session:
        plan = await get_active_plan(session, plan_id)
        if not plan:
            await callback.answer("Тариф не найден")
            return

    await callback.message.answer_invoice(
        title=plan.name,
        description=plan.description or f"VPN подписка на {plan.duration_days} дней",
        payload=f"plan_{plan_id}_{callback.from_user.id}",
        provider_token=PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label=plan.name, amount=plan.price_rub)],
        start_parameter="vpn_subscription",
        need_email=True,
        need_phone_number=True
    )
    await callback.answer()

# Предварительная проверка
@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

# Успешная оплата
@router.message(lambda m: m.successful_payment)
async def successful_payment(message: types.Message):
    payment = message.successful_payment
    payload = payment.invoice_payload  # 'plan_123_456'
    _, plan_id_str, user_id_str = payload.split('_')
    plan_id = int(plan_id_str)
    user_id = int(user_id_str)
    currency = payment.currency
    amount = payment.total_amount
    method = 'stars' if currency == 'XTR' else 'yookassa'

    async with get_session() as session:
        # Сохраняем транзакцию
        await add_transaction(session, user_id, amount, currency, method, str(payment))

        # Получаем план
        plan = await get_active_plan(session, plan_id)
        if not plan:
            await message.answer("Ошибка: тариф не найден")
            return

        # Выбираем сервер
        server = await get_least_loaded_server(session)
        if not server:
            await message.answer("Нет доступных серверов. Обратитесь к администратору.")
            return

        # Создаём клиента на сервере
        xui = XUIClient(server.api_url, server.api_username, server.api_password)
        client_id = await xui.add_client(plan.duration_days)
        if not client_id:
            await message.answer("Ошибка при создании подписки. Попробуйте позже.")
            return

        # Обновляем счётчик клиентов на сервере
        server.current_clients += 1

        # Создаём подписку
        end_date = datetime.datetime.now() + datetime.timedelta(days=plan.duration_days)
        await create_subscription(session, user_id, plan_id, client_id, server.id, end_date)

        await session.commit()

    # Получаем конфиг (заглушка)
    config_data = await xui.get_client_config(client_id)  # нужно реализовать

    await message.answer(f"Подписка активирована до {end_date.strftime('%d.%m.%Y')}.")
    await message.answer_document(
        types.BufferedInputFile(config_data.encode('utf-8'), filename="config.conf"),
        caption="Ваш конфигурационный файл"
    )