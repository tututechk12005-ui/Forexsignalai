"""Order Block Detection."""
from typing import Optional


def detect_order_block(candles: list) -> Optional[dict]:
    if len(candles) < 10:
        return None
    for i in range(len(candles) - 3, 2, -1):
        c0   = candles[i]
        c1   = candles[i + 1]
        c2   = candles[i + 2] if i + 2 < len(candles) else None
        # Bullish OB: last bearish candle before a strong bullish move
        if c0["close"] < c0["open"]:
            if c1["close"] > c1["open"] and c1["close"] > c0["high"]:
                if c2 is None or c2["close"] > c0["high"]:
                    return {"type": "bullish", "top": c0["open"], "bottom": c0["close"], "index": i}
        # Bearish OB: last bullish candle before a strong bearish move
        if c0["close"] > c0["open"]:
            if c1["close"] < c1["open"] and c1["close"] < c0["low"]:
                if c2 is None or c2["close"] < c0["low"]:
                    return {"type": "bearish", "top": c0["close"], "bottom": c0["open"], "index": i}
    return None


def price_in_order_block(price: float, ob: dict) -> bool:
    return ob["bottom"] <= price <= ob["top"]
