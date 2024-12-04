import asyncio
import os
import aiohttp
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot
from bybit_api import get_usdt_perpetual_symbols, get_kline_with_retries
from helpers import analyze_candles
from messaging import run_message_workers
from logging_config import setup_logger

# Класс для хранения общего состояния
class SharedState:
    def __init__(self, message_limit):
        self.message_limit = message_limit
        self.messages_sent = 0
        self.lock = asyncio.Lock()
        self.limit_reached_event = asyncio.Event()

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
MESSAGE_LIMIT = int(os.getenv('MESSAGE_LIMIT', 10))  # Добавлено

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("BOT_TOKEN и CHAT_ID должны быть установлены в .env файле.")

logger = setup_logger(log_file='app.log', level=logging.INFO)
bot = Bot(token=BOT_TOKEN)

async def process_symbol(symbol: str, intervals: dict, session: aiohttp.ClientSession,
                         semaphore: asyncio.Semaphore, message_queue: asyncio.Queue,
                         shared_state: SharedState):
    """
    Обрабатывает символ на указанных интервалах и объединяет сигналы для одного символа.
    """
    async with semaphore:
        if shared_state.limit_reached_event.is_set():
            # Достигнут лимит сообщений, пропускаем обработку
            return

        signals = {}  # Для хранения сигналов
        for interval_key, interval_value in intervals.items():
            if shared_state.limit_reached_event.is_set():
                # Достигнут лимит сообщений, пропускаем обработку
                return

            try:
                # Увеличено количество свечей для расчета MACD (26 + 9 = 35)
                kline_data = await get_kline_with_retries(session, symbol, interval_key, limit=36)
                if not kline_data:
                    logger.warning(f"Нет данных свечей для {symbol} на интервале {interval_value}.")
                    continue

                fields = ['start', 'open', 'high', 'low', 'close', 'volume']
                candles = [dict(zip(fields, candle)) for candle in kline_data[:-1]]  # Исключаем последнюю свечу

                analysis = analyze_candles(candles)

                signal = analysis.get('signal')
                percent_k = analysis.get('%K')
                percent_d = analysis.get('%D')
                macd = analysis.get('MACD')

                # Логируем значения индикаторов
                if percent_k is not None and percent_d is not None and macd is not None:
                    logger.info(f"{symbol} | {interval_value} | %K: {percent_k:.5f} | %D: {percent_d:.5f} | MACD: {macd:.7f}")
                else:
                    logger.warning(f"{symbol} | {interval_value} | Недостаточно данных для индикаторов")

                # Отправка сигналов только если все индикаторы присутствуют и являются числами
                if signal and isinstance(percent_k, (float, int)) and isinstance(percent_d, (float, int)) and isinstance(macd, (float, int)):
                    trade_action = "🔴 SHORT" if signal == "short" else "🟢 LONG"

                    # Инициализация списка сигналов для символа
                    if symbol not in signals:
                        signals[symbol] = {
                            'intervals': [],
                            'trade_action': trade_action,
                            'percent_k': percent_k,
                            'percent_d': percent_d,
                            'macd': macd
                        }
                    else:
                        # Обновляем последние значения
                        signals[symbol]['percent_k'] = percent_k
                        signals[symbol]['percent_d'] = percent_d
                        signals[symbol]['macd'] = macd

                    signals[symbol]['intervals'].append(interval_value)

            except aiohttp.ClientResponseError as e:
                logger.error(f"Ошибка при получении данных свечей для {symbol}: {e.status}, {e.message}, URL: {e.request_info.url}")
            except aiohttp.ContentTypeError as e:
                logger.error(f"Неверный тип содержимого при получении данных для {symbol}: {e}")
            except Exception as e:
                logger.error(f"Ошибка при обработке символа {symbol} на интервале {interval_value}: {e}")

        # Формируем сообщение для символа, если есть сигналы
        for symbol, data in signals.items():
            if shared_state.limit_reached_event.is_set():
                # Достигнут лимит сообщений, пропускаем обработку
                return

            intervals_text = ", ".join(data['intervals'])
            trade_action = data['trade_action']
            percent_k = data.get('percent_k')
            percent_d = data.get('percent_d')
            macd = data.get('macd')

            # Проверяем, что значения числовые перед форматированием
            if not (isinstance(percent_k, (float, int)) and isinstance(percent_d, (float, int)) and isinstance(macd, (float, int))):
                logger.warning(f"Не все индикаторы числовые для {symbol} на интервале {intervals_text}. Сообщение не будет отправлено.")
                continue

            percent_k_formatted = f"{percent_k:.5f}"
            percent_d_formatted = f"{percent_d:.5f}"
            macd_formatted = f"{macd:.7f}"

            message = (
                f"🔥 #{symbol}\n"
                f"🕒 {intervals_text}\n"
                f"{trade_action}\n"
                f"%K: {percent_k_formatted}\n"
                f"%D: {percent_d_formatted}\n"
                f"MACD: {macd_formatted}\n"
            )

            # Попытка увеличить счётчик сообщений
            async with shared_state.lock:
                if shared_state.messages_sent >= shared_state.message_limit:
                    shared_state.limit_reached_event.set()
                    logger.info("Достигнут лимит сообщений. Остановка дальнейшей обработки.")
                    return
                shared_state.messages_sent += 1

            await message_queue.put(message)

async def main():
    """
    Главная функция.
    """
    is_manual_run = os.getenv("MANUAL_RUN", "false").lower() == "true"
    current_minute = datetime.now().minute

    # Определяем интервалы на основе текущей минуты
    intervals = {
        '5': '5m',
        '15': '15m'
    }

    # Фильтруем интервалы на основе времени запуска
    if not is_manual_run:  # Если скрипт не запущен вручную
        if current_minute % 15 == 0:
            intervals = {k: v for k, v in intervals.items() if k in ['15', '5']}
        elif current_minute % 5 == 0:
            intervals = {k: v for k, v in intervals.items() if k in ['5']}
        else:
            logger.info("Скрипт запущен в неподходящее время. Завершение.")
            return

    # Ограничение количества одновременных задач
    MAX_CONCURRENT_TASKS = 50
    MAX_WORKERS = 5  # Количество воркеров для отправки сообщений
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    message_queue = asyncio.Queue()

    shared_state = SharedState(message_limit=MESSAGE_LIMIT)

    async with aiohttp.ClientSession() as session:
        symbols = await get_usdt_perpetual_symbols()
        symbols = [symbol for symbol in symbols if symbol.upper() != 'USDCUSDT']
        # logger.info(f"Доступные символы для USDT бессрочных контрактов: {symbols}")

        if not symbols:
            await send_telegram_message(bot, CHAT_ID, "❌ Список символов пуст.", logger)
            return

        # Запускаем обработчик сообщений с несколькими воркерами
        worker_task = asyncio.create_task(
            run_message_workers(
                bot,
                CHAT_ID,
                message_queue,
                logger,
                max_workers=MAX_WORKERS
            )
        )

        tasks = [
            process_symbol(symbol, intervals, session, semaphore, message_queue, shared_state)
            for symbol in symbols
        ]

        await asyncio.gather(*tasks)

        # Завершаем очередь сообщений, отправляя "EXIT" для каждого воркера
        for _ in range(MAX_WORKERS):
            await message_queue.put("EXIT")
        await worker_task

if __name__ == "__main__":
    asyncio.run(main())
