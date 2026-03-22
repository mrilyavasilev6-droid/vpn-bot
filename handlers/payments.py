from aiogram import Router, types
from aiogram.types import LabeledPrice, PreCheckoutQuery
from config import PROVIDER_TOKEN
from database.session import AsyncSessionLocal
from database.models import Plan, User, Subscription, Server, ReferralBonus, Transaction
from vpn.xui import XUIClient
import datetime

router = Router()

@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(lambda m: m.successful_payment)
async def successful_payment(message: types.Message):
    payment = message.successful_payment
    payload = payment.invoice_payload  # 'plan_123_456'
    _, plan_id_str, user_id_str = payload.split('_')
    plan_id = int(plan_id_str)
    user_id = int(user_id_str)

    async with AsyncSessionLocal() as session:
        # Сохраняем транзакцию
        tx = Transaction(
            user_id=user_id,
            amount=payment.total_amount,
            currency=payment.currency,
            payment_method='yookassa',
            status='completed',
            telegram_payload=str(payment)
        )
        session.add(tx)

        plan = await session.get(Plan, plan_id)
        if not plan:
            await message.answer("Ошибка: тариф не найден")
            return

        # Выбираем сервер
        servers = await session.execute(
            select(Server).where(Server.max_clients > Server.current_clients)
        )
        servers = servers.scalars().all()
        if not servers:
            await message.answer("Нет доступных серверов. Обратитесь к администратору.")
            return
        server = min(servers, key=lambda s: s.current_clients / s.max_clients if s.max_clients else 0)

        # Создаём клиента на сервере
        xui = XUIClient(server.api_url, server.api_username, server.api_password)
        client_id = await xui.add_client(plan.duration_days)
        if not client_id:
            await message.answer("Ошибка создания подписки. Попробуйте позже.")
            return

        server.current_clients += 1

        end_date = datetime.datetime.now() + datetime.timedelta(days=plan.duration_days)
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            client_id=client_id,
            server_id=server.id,
            end_date=end_date,
            is_active=True
        )
        session.add(subscription)

        # Реферальная система: начисляем бонус рефереру
        user = await session.get(User, user_id)
        if user and user.referral_by:
            existing = await session.execute(
                select(ReferralBonus).where(ReferralBonus.referred_id == user_id)
            )
            if not existing.scalar_one_or_none():
                referrer = await session.get(User, user.referral_by)
                # Начисляем 7 дней к подписке реферера
                referrer_sub = await session.execute(
                    select(Subscription).where(Subscription.user_id == user.referral_by, Subscription.is_active == True)
                )
                referrer_sub = referrer_sub.scalar_one_or_none()
                if referrer_sub:
                    referrer_sub.end_date += datetime.timedelta(days=7)
                else:
                    # Создаём подписку на 7 дней (без плана)
                    # Можно использовать план с duration=7, если есть
                    pass
                bonus = ReferralBonus(referrer_id=user.referral_by, referred_id=user_id, bonus_days=7)
                session.add(bonus)

        await session.commit()

    # Получаем конфиг (реализовать в xui)
    config_data = await xui.get_client_config(client_id)  # заглушка

    await message.answer(f"Подписка активирована до {end_date.strftime('%d.%m.%Y')}.")
    await message.answer_document(
        types.BufferedInputFile(config_data.encode('utf-8'), filename="config.conf"),
        caption="Ваш конфигурационный файл"
    )
