import qrcode
from io import BytesIO
from datetime import datetime

def format_date(dt: datetime) -> str:
    return dt.strftime('%d.%m.%Y')

def generate_qr(data: str) -> BytesIO:
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf
