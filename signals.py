"""Enhanced signal generation engine — SMC + Trend confirmation."""
import logging
from typing import Optional
from utils.api import fetch_ohlcv
from utils.helpers import is_pair_tradeable
from smc.bos import detect_bos
from smc.choch import detect_choch
from smc.liquidity import detect_liquidity_sweep
from smc.orderblocks import detect_order_block
from smc.fvg import detect_fvg
from smc.trend import detect_trend
from database import save_signal, get_setting, get_latest_signal
from config import TIMEFRAMES

logger = logging.getLogger(__name__)


# ── internal helpers ──────────────────────────────────────────────────────────

def _atr(candles: list) -> float:
    if len(candles) < 2:
        return 0.001
    trs = []
    for i in range(1, len(candles)):
        c   = candles[i]
        pc  = candles[i-1]["close"]
        trs.append(max(c["high"]-c["low"], abs(c["high"]-pc), abs(c["low"]-pc)))
    return sum(trs) / len(trs) if trs else 0.001


def _score(bos, choch, sweep, ob, fvg, trend):
    bull = bear = 0
    if bos   == "bullish":        bull += 3
    elif bos == "bearish":        bear += 3
    if choch  == "bullish":       bull += 3
    elif choch== "bearish":       bear += 3
    if sweep  == "bullish_sweep": bull += 2
    elif sweep== "bearish_sweep": bear += 2
    if ob:
        if ob["type"] == "bullish": bull += 2
        else:                        bear += 2
    if fvg:
        if fvg["type"] == "bullish": bull += 1
        else:                         bear += 1
    # Trend confirmation adds a significant bonus
    if trend  == "bullish":       bull += 3
    elif trend== "bearish":       bear += 3
    return bull, bear


def _direction_and_confidence(bull, bear):
    total = bull + bear
    if total == 0:
        return "WAIT", 0
    if bull > bear:
        conf = min(int((bull / (total + 1)) * 100), 97)
        return "BUY", conf
    if bear > bull:
        conf = min(int((bear / (total + 1)) * 100), 97)
        return "SELL", conf
    return "WAIT", 50


def _calculate_levels(candles, direction, ob, fvg):
    last    = candles[-1]["close"]
    atr_val = _atr(candles[-14:])
    s_high  = max(c["high"] for c in candles[-20:])
    s_low   = min(c["low"]  for c in candles[-20:])

    if direction == "BUY":
        if ob and ob["type"] == "bullish":
            entry = (ob["top"] + ob["bottom"]) / 2
        elif fvg and fvg["type"] == "bullish":
            entry = fvg["midpoint"]
        else:
            entry = last
        sl  = s_low  - atr_val * 0.5
        risk = abs(entry - sl)
        tp1 = entry + risk * 1.5
        tp2 = entry + risk * 2.5
        tp3 = entry + risk * 4.0
    else:
        if ob and ob["type"] == "bearish":
            entry = (ob["top"] + ob["bottom"]) / 2
        elif fvg and fvg["type"] == "bearish":
            entry = fvg["midpoint"]
        else:
            entry = last
        sl   = s_high + atr_val * 0.5
        risk = abs(sl - entry)
        tp1  = entry - risk * 1.5
        tp2  = entry - risk * 2.5
        tp3  = entry - risk * 4.0

    return (round(v, 5) for v in (entry, sl, tp1, tp2, tp3))


# ── public API ────────────────────────────────────────────────────────────────

async def analyze_pair(pair: str, timeframe: str) -> Optional[dict]:
    """Run full SMC + trend analysis on one pair/timeframe."""
    candles = await fetch_ohlcv(pair, timeframe, outputsize=100)
    if not candles or len(candles) < 55:
        logger.warning("Insufficient candles for %s %s", pair, timeframe)
        return None

    bos   = detect_bos(candles)
    choch = detect_choch(candles)
    sweep = detect_liquidity_sweep(candles)
    ob    = detect_order_block(candles)
    fvg   = detect_fvg(candles)
    trend = detect_trend(candles)

    flags = {
        "bos":         bos   is not None,
        "choch":       choch is not None,
        "liquidity":   sweep is not None,
        "order_block": ob    is not None,
        "fvg":         fvg   is not None,
        "trend_ok":    trend is not None,
    }

    bull, bear    = _score(bos, choch, sweep, ob, fvg, trend)
    direction, confidence = _direction_and_confidence(bull, bear)

    if direction == "WAIT":
        return None

    entry, sl, tp1, tp2, tp3 = _calculate_levels(candles, direction, ob, fvg)
    risk   = abs(entry - sl)
    reward = abs(tp1 - entry)
    rr     = round(reward / risk, 2) if risk > 0 else 0.0

    return {
        "pair":         pair,
        "timeframe":    timeframe,
        "direction":    direction,
        "entry":        entry,
        "stop_loss":    sl,
        "take_profit1": tp1,
        "take_profit2": tp2,
        "take_profit3": tp3,
        "risk_reward":  rr,
        "confidence":   confidence,
        "flags":        flags,
    }


async def generate_signal_for_pair(pair: str) -> Optional[dict]:
    """
    Multi-timeframe analysis — returns the highest-confidence signal
    that meets the configured threshold. Saves to DB.
    """
    if not is_pair_tradeable(pair):
        return None

    min_conf    = int(get_setting("min_confidence", "80"))
    best_signal = None

    for tf in TIMEFRAMES:
        try:
            sig = await analyze_pair(pair, tf)
        except Exception as e:
            logger.error("analyze_pair error %s %s: %s", pair, tf, e)
            continue
        if sig is None:
            continue
        if sig["confidence"] >= min_conf:
            if best_signal is None or sig["confidence"] > best_signal["confidence"]:
                best_signal = sig

    if best_signal:
        f   = best_signal["flags"]
        sig_id = save_signal(
            pair       = best_signal["pair"],
            timeframe  = best_signal["timeframe"],
            direction  = best_signal["direction"],
            entry      = best_signal["entry"],
            stop_loss  = best_signal["stop_loss"],
            tp1        = best_signal["take_profit1"],
            tp2        = best_signal["take_profit2"],
            tp3        = best_signal["take_profit3"],
            rr         = best_signal["risk_reward"],
            confidence = best_signal["confidence"],
            flags      = f,
        )
        best_signal["id"] = sig_id

    return best_signal


async def scan_all_pairs() -> list:
    """Scan all enabled pairs and return list of signals."""
    from config import SUPPORTED_PAIRS
    enabled_raw = get_setting("enabled_pairs", ",".join(SUPPORTED_PAIRS))
    enabled     = [p.strip() for p in enabled_raw.split(",") if p.strip()]
    results     = []
    for pair in enabled:
        try:
            sig = await generate_signal_for_pair(pair)
            if sig:
                results.append(sig)
        except Exception as e:
            logger.error("scan error %s: %s", pair, e)
    return results
