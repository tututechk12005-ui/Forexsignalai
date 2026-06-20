"""Break of Structure (BOS) detection."""
from typing import Optional


def detect_bos(candles: list) -> Optional[str]:
    if len(candles) < 20:
        return None
    recent     = candles[-20:]
    swing_high = max(c["high"]  for c in recent[:-5])
    swing_low  = min(c["low"]   for c in recent[:-5])
    last       = candles[-1]
    if last["high"] > swing_high and last["close"] > swing_high:
        return "bullish"
    if last["low"] < swing_low and last["close"] < swing_low:
        return "bearish"
    return None


def get_swing_levels(candles: list, lookback: int = 10):
    if len(candles) < lookback + 2:
        return None, None
    window = candles[-(lookback + 2):-1]
    return max(c["high"] for c in window), min(c["low"] for c in window)
