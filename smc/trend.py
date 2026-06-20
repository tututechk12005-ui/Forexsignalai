"""Trend confirmation using EMA alignment."""
from typing import Optional


def _ema(values: list, period: int) -> list:
    if len(values) < period:
        return []
    k      = 2 / (period + 1)
    result = [sum(values[:period]) / period]
    for v in values[period:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def detect_trend(candles: list) -> Optional[str]:
    """
    Returns 'bullish', 'bearish', or None based on EMA20 vs EMA50 alignment.
    Also checks EMA slope for extra confirmation.
    """
    if len(candles) < 55:
        return None
    closes = [c["close"] for c in candles]
    ema20  = _ema(closes, 20)
    ema50  = _ema(closes, 50)
    if not ema20 or not ema50:
        return None
    last20 = ema20[-1]
    last50 = ema50[-1]
    slope20 = ema20[-1] - ema20[-3] if len(ema20) >= 3 else 0
    if last20 > last50 and slope20 > 0:
        return "bullish"
    if last20 < last50 and slope20 < 0:
        return "bearish"
    return None
