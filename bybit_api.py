# bybit_api.py
import logging
import aiohttp
import asyncio

API_BASE_URL = "https://api.bybit.com/v5/market/"

async def get_usdt_perpetual_symbols():
    url = f"{API_BASE_URL}instruments-info"
    params = {
        "category": "linear"
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                data = await response.json()
                if data['retCode'] == 0:
                    symbols = [
                        symbol['symbol'] for symbol in data['result']['list']
                        if symbol['contractType'] == 'LinearPerpetual' and
                           symbol['settleCoin'] == 'USDT' and
                           symbol['status'] == 'Trading'
                    ]
                    return symbols
                else:
                    logging.error(f"Ошибка при получении списка символов: {data['retMsg']}")
                    return []
        except Exception as e:
            logging.exception(f"Произошла ошибка при получении списка символов: {e}")
            return []

async def get_historical_kline_data(session, symbol, interval, limit):
    url = f"{API_BASE_URL}kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    try:
        async with session.get(url, params=params) as response:
            data = await response.json()
            if data['retCode'] == 0 and data['result']:
                candle_list = data['result']['list']
                candle_list = candle_list[::-1]
                return candle_list
            else:
                logging.error(f"Ошибка при получении данных свечей для {symbol}: {data['retMsg']}")
                return []
    except Exception as e:
        logging.exception(f"Произошла ошибка при получении данных свечей для {symbol}: {e}")
        return []

async def get_kline_with_retries(session, symbol, interval, limit, retries=3, delay=1):
    for attempt in range(retries):
        try:
            return await get_historical_kline_data(session, symbol, interval, limit)
        except aiohttp.ClientResponseError as e:
            if attempt < retries - 1:
                logger.warning(f"Попытка {attempt + 1} для {symbol} на интервале {interval} не удалась. Повтор через {delay} сек.")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Ошибка при получении данных для {symbol} на интервале {interval}: {e}")
                return None
        except aiohttp.ContentTypeError as e:
            logger.error(f"Неверный тип содержимого для {symbol} на интервале {interval}: {e}")
            return None
        except Exception as e:
            logger.error(f"Неизвестная ошибка для {symbol} на интервале {interval}: {e}")
            return None
