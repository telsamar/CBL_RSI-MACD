# helpers.py
from typing import List, Dict, Optional, Tuple
from stochastic_oscillator import calculate_stochastic_oscillator
from macd import calculate_macd
import os

def analyze_candles(candles: List[Dict[str, float]], k_period: int = 14, d_period: int = 3,
                   fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, Optional[Dict]]:
    """
    Анализирует свечи на основе Стохастического осциллятора и MACD.

    :param candles: Список свечей (от старых к новым) в формате List[Dict].
    :param k_period: Период для расчета %K.
    :param d_period: Период для расчета %D.
    :param fast_period: Период быстрой EMA для MACD.
    :param slow_period: Период медленной EMA для MACD.
    :param signal_period: Период сигнальной линии для MACD.
    :return: Анализ с сигналами.
    """
    analysis = {}
    
    # Получение параметров из переменных окружения
    k_period = int(os.getenv("K_PERIOD", k_period))
    d_period = int(os.getenv("D_PERIOD", d_period))
    fast_period = int(os.getenv("FAST_PERIOD", fast_period))
    slow_period = int(os.getenv("SLOW_PERIOD", slow_period))
    signal_period = int(os.getenv("SIGNAL_PERIOD", signal_period))
    
    # Рассчет Стохастического осциллятора
    percent_k, percent_d = calculate_stochastic_oscillator(candles, k_period, d_period)
    analysis['%K'] = percent_k
    analysis['%D'] = percent_d

    # Рассчет MACD
    macd, signal, histogram = calculate_macd(candles, fast_period, slow_period, signal_period)
    analysis['MACD'] = macd
    analysis['Signal'] = signal
    analysis['Histogram'] = histogram

    # Зоны перекупленности и перепроданности из переменных окружения
    overbought = float(os.getenv("OVERBOUGHT"))
    oversold = float(os.getenv("OVERSOLD"))

    # Определение сигналов на основе условий
    signal_long = False
    signal_short = False

    # Условия генерации сигналов только при наличии всех индикаторов
    if percent_k is not None and percent_d is not None and macd is not None:
        if percent_k < oversold and percent_d < oversold:
            signal_long = True
        elif percent_k > overbought and percent_d > overbought:
            signal_short = True

    if signal_long:
        analysis['signal'] = 'long'
    elif signal_short:
        analysis['signal'] = 'short'
    else:
        analysis['signal'] = None

    return analysis
