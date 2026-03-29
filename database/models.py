from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    referral_by = Column(BigInteger, ForeignKey('users.user_id', ondelete='SET NULL'))
    balance = Column(Integer, default=0)          # баланс в рублях (копейки)
    auto_renew = Column(Boolean, default=False)   # автопродление
    trial_used = Column(Boolean, default=False)   # использовал ли пробный период
    trial_end_date = Column(DateTime, nullable=True)  # дата окончания пробного периода (если активен)
    marzban_username = Column(String(255), unique=True, nullable=True)  # имя пользователя в Marzban

class Plan(Base):
    __tablename__ = 'plans'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    duration_days = Column(Integer, nullable=False)
    price_stars = Column(Integer, nullable=False)   # цена в Telegram Stars
    price_rub = Column(Integer, nullable=False)     # цена в рублях (копейки)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

class Server(Base):
    __tablename__ = 'servers'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    host = Column(String(255), nullable=False)
    api_url = Column(String(255), nullable=False)
    api_username = Column(String(100))
    api_password = Column(String(100))
    location = Column(String(100))
    max_clients = Column(Integer, default=0)
    current_clients = Column(Integer, default=0)

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'))
    plan_id = Column(Integer, ForeignKey('plans.id'))
    client_id = Column(String(255))          # ID клиента в VPN-панели (в Marzban это username)
    server_id = Column(Integer, ForeignKey('servers.id'))
    start_date = Column(DateTime, server_default=func.now())
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    amount = Column(Integer, nullable=False)          # сумма в копейках или звездах
    currency = Column(String(10), nullable=False)     # 'XTR', 'RUB'
    payment_method = Column(String(20))               # 'stars', 'yookassa', 'crypto'
    status = Column(String(20), default='pending')
    telegram_payload = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class ReferralBonus(Base):
    __tablename__ = 'referral_bonuses'
    id = Column(Integer, primary_key=True)
    referrer_id = Column(BigInteger, ForeignKey('users.user_id'))
    referred_id = Column(BigInteger, ForeignKey('users.user_id'))
    bonus_days = Column(Integer)          # сколько дней добавилось к подписке реферера
    awarded_at = Column(DateTime, server_default=func.now())

class Trial(Base):
    __tablename__ = 'trials'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    start_date = Column(DateTime, server_default=func.now())
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
