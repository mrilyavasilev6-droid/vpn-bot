import qrcode
from io import BytesIO
from datetime import datetime, timedelta

def format_date(dt: datetime) -> str:
    """Форматирует дату в строку 'DD.MM.YYYY'"""
    return dt.strftime('%d.%m.%Y')

def generate_qr(data: str) -> BytesIO:
    """Генерирует QR-код из строки и возвращает BytesIO"""
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

def days_left(end_date: datetime) -> int:
    """Возвращает количество дней до окончания подписки"""
    return (end_date - datetime.now()).days