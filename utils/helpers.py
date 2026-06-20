from datetime import datetime
from config import SUBSCRIPTION_PLANS, FOREX_PAIRS


def format_price(value: float, pair: str) -> str:
    if "JPY" in pair:
        return f"{value:.3f}"
    if pair in ("XAUUSD",):
        return f"{value:.2f}"
    if pair in ("BTCUSD",):
        return f"{value:.2f}"
    return f"{value:.5f}"


def format_signal_message(signal: dict) -> str:
    pair      = signal["pair"]
    direction = signal["direction"]
    tf        = signal["timeframe"]
    entry     = format_price(signal["entry"],        pair)
    sl        = format_price(signal["stop_loss"],    pair)
    tp1       = format_price(signal["take_profit1"], pair)
    tp2       = format_price(signal["take_profit2"], pair)
    tp3       = format_price(signal.get("take_profit3", signal["take_profit2"]), pair)
    rr        = signal["risk_reward"]
    conf      = signal["confidence"]
    gen_at    = signal.get("generated_at", "")[:16]

    arrow = "📈" if direction == "BUY" else "📉"

    flags = []
    if signal.get("bos"):        flags.append("BOS ✅")
    if signal.get("choch"):      flags.append("CHoCH ✅")
    if signal.get("liquidity"):  flags.append("Liquidity ✅")
    if signal.get("order_block"):flags.append("OB ✅")
    if signal.get("fvg"):        flags.append("FVG ✅")
    if signal.get("trend_ok"):   flags.append("Trend ✅")

    confluence = " | ".join(flags) if flags else "None"

    msg = (
        f"┌─────────────────────────┐\n"
        f"│  {arrow} *SMC SIGNAL ALERT*  │\n"
        f"└─────────────────────────┘\n\n"
        f"📊 *Pair:* `{pair}`\n"
        f"📈 *Signal:* `{direction}`\n"
        f"⏱ *Timeframe:* `{tf}`\n\n"
        f"🎯 *Entry:* `{entry}`\n"
        f"🛑 *Stop Loss:* `{sl}`\n\n"
        f"✅ *TP1:* `{tp1}`\n"
        f"✅ *TP2:* `{tp2}`\n"
        f"✅ *TP3:* `{tp3}`\n\n"
        f"⚖️ *Risk/Reward:* `1:{rr:.1f}`\n"
        f"🔥 *Accuracy Score:* `{conf}%`\n\n"
        f"🧠 *SMC Confluence:*\n`{confluence}`\n\n"
        f"🕒 *Generated:* `{gen_at}`\n\n"
        f"─────────────────────────\n"
        f"⚠️ _This signal is generated automatically from market analysis and is not financial advice. "
        f"Trading decisions remain the user's responsibility._"
    )
    return msg


def format_result_message(signal: dict, result: str) -> str:
    pair      = signal["pair"]
    direction = signal["direction"]
    entry     = format_price(signal["entry"], pair)

    if result == "tp1":
        return (
            f"🎯 *TP1 HIT — {pair}* 🎉\n\n"
            f"Direction: `{direction}`\n"
            f"Entry was: `{entry}`\n"
            f"TP1 reached: `{format_price(signal['take_profit1'], pair)}`\n\n"
            f"✅ Consider moving stop loss to breakeven for TP2 & TP3.\n"
            f"⚠️ _Not financial advice._"
        )
    else:
        return (
            f"🛑 *STOP LOSS HIT — {pair}*\n\n"
            f"Direction: `{direction}`\n"
            f"Entry was: `{entry}`\n"
            f"SL: `{format_price(signal['stop_loss'], pair)}`\n\n"
            f"📉 Setup invalidated. Wait for next quality setup.\n"
            f"💡 _Risk management is key. Never risk more than you can afford._\n"
            f"⚠️ _Not financial advice._"
        )


def is_forex_market_closed() -> bool:
    """Returns True if the Forex market is currently closed (weekend)."""
    day = datetime.utcnow().weekday()
    return day >= 5  # 5=Saturday, 6=Sunday


def is_pair_tradeable(pair: str) -> bool:
    """Crypto pairs trade 24/7; forex pairs are closed on weekends."""
    from config import FOREX_PAIRS
    if pair in FOREX_PAIRS:
        return not is_forex_market_closed()
    return True


def plan_display_name(plan_key: str) -> str:
    return SUBSCRIPTION_PLANS.get(plan_key, {}).get("name", plan_key)


def days_until(date_str: str) -> int:
    try:
        end   = datetime.fromisoformat(date_str)
        delta = end - datetime.utcnow()
        return max(0, delta.days)
    except Exception:
        return 0
