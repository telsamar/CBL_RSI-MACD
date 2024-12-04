# logging_config.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name='telegram_signal_logger', log_file='app.log', level=logging.INFO):
    """
    Настраивает логгер с заданными параметрами.

    :param name: Имя логгера.
    :param log_file: Путь к лог-файлу.
    :param level: Уровень логирования.
    :return: Настроенный логгер.
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Используем RotatingFileHandler для ротации логов
    file_handler = RotatingFileHandler(log_file, mode='w')  # Режим 'w' для перезаписи
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.setLevel(level)

    return logger
