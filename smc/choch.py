"""Change of Character (CHOCH) detection."""
from typing import Optional


def detect_choch(candles: list) -> Optional[str]:
    if len(candles) < 30:
        return None
    seg      = candles[-30:]
    first15  = seg[:15]
    last15   = seg[15:]
    hh_first = _count_hh(first15)
    ll_first = _count_ll(first15)
    hh_last  = _count_hh(last15)
    ll_last  = _count_ll(last15)
    if ll_first >= 2 and hh_last >= 1:
        return "bullish"
    if hh_first >= 2 and ll_last >= 1:
        return "bearish"
    return None


def _count_hh(c):
    return sum(1 for i in range(1, len(c)) if c[i]["high"] > c[i-1]["high"])


def _count_ll(c):
    return sum(1 for i in range(1, len(c)) if c[i]["low"] < c[i-1]["low"])
