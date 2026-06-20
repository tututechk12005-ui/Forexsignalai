"""Liquidity Sweep Detection."""
from typing import Optional


def detect_liquidity_sweep(candles: list) -> Optional[str]:
    if len(candles) < 15:
        return None
    lookback   = candles[-15:-1]
    last       = candles[-1]
    swing_low  = min(c["low"]  for c in lookback)
    swing_high = max(c["high"] for c in lookback)
    if last["low"] < swing_low and last["close"] > swing_low:
        return "bullish_sweep"
    if last["high"] > swing_high and last["close"] < swing_high:
        return "bearish_sweep"
    return None


def get_liquidity_pools(candles: list, lookback: int = 20) -> dict:
    if len(candles) < lookback:
        return {}
    window = candles[-lookback:]
    return {
        "buy_side":  max(c["high"] for c in window),
        "sell_side": min(c["low"]  for c in window),
    }
