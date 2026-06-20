"""Fair Value Gap (FVG) Detection."""
from typing import Optional


def detect_fvg(candles: list) -> Optional[dict]:
    if len(candles) < 3:
        return None
    for i in range(len(candles) - 3, 0, -1):
        c0, c1, c2 = candles[i], candles[i+1], candles[i+2]
        if c2["low"] > c0["high"]:
            return {"type": "bullish", "top": c2["low"],  "bottom": c0["high"],
                    "midpoint": (c2["low"] + c0["high"]) / 2}
        if c2["high"] < c0["low"]:
            return {"type": "bearish", "top": c0["low"],  "bottom": c2["high"],
                    "midpoint": (c0["low"] + c2["high"]) / 2}
    return None


def price_in_fvg(price: float, fvg: dict) -> bool:
    return fvg["bottom"] <= price <= fvg["top"]
