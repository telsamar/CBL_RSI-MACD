# stochastic_oscillator.py
from typing import List, Dict, Tuple, Optional

def calculate_stochastic_oscillator(candles: List[Dict[str, float]], k_period: int = 14, d_period: int = 3) -> Tuple[Optional[float], Optional[float]]:
    """
    Рассчитывает Стохастический осциллятор (%K и %D).

    :param candles: Список свечей (от старых к новым) в формате List[Dict].
    :param k_period: Период для расчёта %K.
    :param d_period: Период для расчёта %D.
    :return: Последние значения %K и %D.
    """
    if len(candles) < k_period + d_period - 1:
        return None, None

    # Извлекаем необходимые данные из словарей
    relevant_candles = candles[-(k_period + d_period - 1):]
    highs = [float(candle['high']) for candle in relevant_candles]
    lows = [float(candle['low']) for candle in relevant_candles]
    closes = [float(candle['close']) for candle in relevant_candles]

    # Рассчитываем %K без сглаживания
    percent_k_list = []
    for i in range(k_period - 1, len(closes)):
        highest_high = max(highs[i - k_period + 1:i + 1])
        lowest_low = min(lows[i - k_period + 1:i + 1])
        current_close = closes[i]

        if highest_high == lowest_low:
            percent_k = 0  # Или другое значение по вашему усмотрению
        else:
            percent_k = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100

        percent_k_list.append(percent_k)

    if len(percent_k_list) < d_period:
        return None, None

    # Рассчитываем %D как скользящее среднее %K
    percent_d_list = []
    for i in range(d_period - 1, len(percent_k_list)):
        percent_d = sum(percent_k_list[i - d_period + 1:i + 1]) / d_period
        percent_d_list.append(percent_d)

    last_percent_k = percent_k_list[-1]
    last_percent_d = percent_d_list[-1]

    return last_percent_k, last_percent_d
