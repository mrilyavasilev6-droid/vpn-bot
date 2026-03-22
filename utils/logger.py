import logging
import sys

def setup_logger(name: str = "vpn_bot", level=logging.INFO) -> logging.Logger:
    """Настраивает и возвращает логгер"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Можно добавить файловый обработчик
    file_handler = logging.FileHandler('bot.log')
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger