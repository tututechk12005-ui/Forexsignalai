"""Signal handler."""
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from signals import generate_signal_for_pair
from database import get_user, get_latest_signal, get_setting
from utils.helpers import format_signal_message, is_pair_tradeable, is_forex_market_closed
from config import SUPPORTED_PAIRS, ASSETS_DIR

logger = logging.getLogger(__name__)


def _signal_menu_keyboard():
    enabled_raw = get_setting("enabled_pairs", ",".join(SUPPORTED_PAIRS))
    enabled     = [p.strip() for p in enabled_raw.split(",") if p.strip()]
    rows = [[InlineKeyboardButton(p, callback_data=f"signal_{p}")] for p in enabled]
    rows.append([InlineKeyboardButton("🔙 Close", callback_data="close_inline")])
    return InlineKeyboardMarkup(rows)


async def get_signal_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    market_note = ""
    if is_forex_market_closed():
        market_note = (
            "\n\n🔴 *Forex Market Closed*\n"
            "Signals for crypto pairs (XAUUSD, BTCUSD) still available."
        )
    await update.message.reply_text(
        f"💡 *Get Signal*\n\nChoose a pair for SMC analysis:{market_note}",
        parse_mode="Markdown",
        reply_markup=_signal_menu_keyboard(),
    )


async def get_signal_for_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔍 Analysing market…")
    pair = query.data.replace("signal_", "")
    if pair not in SUPPORTED_PAIRS:
        await query.answer("❌ Invalid pair.", show_alert=True)
        return

    # Market closed guard
    if not is_pair_tradeable(pair):
        await query.edit_message_text(
            f"🔴 *Market Closed — {pair}*\n\n"
            "Forex market is currently closed (Saturday/Sunday).\n"
            "No signals are generated during market closure.\n\n"
            "✅ Try XAUUSD or BTCUSD instead.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Close", callback_data="close_inline")]
            ]),
        )
        return

    db_user = get_user(update.effective_user.id)
    is_vip  = db_user.get("is_vip", 0) if db_user else False

    await query.edit_message_text(
        f"🔍 *Analysing {pair}…*\n\n"
        "Running SMC analysis across 15m · 1H · 4H.\nPlease wait ⏳",
        parse_mode="Markdown",
    )

    try:
        signal = await generate_signal_for_pair(pair)
    except Exception as e:
        logger.error("Signal error %s: %s", pair, e)
        signal = None

    # Fallback to last cached signal
    if not signal:
        cached = get_latest_signal(pair)
        if cached:
            signal = dict(cached)
            signal["_from_cache"] = True

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data=f"signal_{pair}")],
        [InlineKeyboardButton("📊 Select Pair", callback_data="pairs_menu")],
        [InlineKeyboardButton("🔙 Close",      callback_data="close_inline")],
    ])

    if not signal:
        await query.edit_message_text(
            f"⚠️ *No qualifying signal for {pair} right now.*\n\n"
            f"Minimum confidence threshold: `{get_setting('min_confidence','80')}%`\n"
            "The market is in consolidation or no strong SMC setup detected.\n\n"
            "🕒 Try again in 15 minutes.",
            parse_mode="Markdown",
            reply_markup=kb,
        )
        return

    # Gate full signal behind VIP
    if not is_vip and signal.get("confidence", 0) >= 80:
        banner = os.path.join(ASSETS_DIR, "premium_banner.png")
        text = (
            f"🔒 *High-Confidence Signal Available — {pair}!*\n\n"
            f"Direction: `{'🟢 BUY' if signal['direction'] == 'BUY' else '🔴 SELL'}`\n"
            f"Accuracy Score: `{signal['confidence']}%`\n\n"
            "⭐ *Upgrade to VIP to unlock full Entry, SL & TP levels.*"
        )
        vip_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Get VIP Access", callback_data="subscription_menu")],
            [InlineKeyboardButton("🔙 Close", callback_data="close_inline")],
        ])
        if os.path.exists(banner):
            await query.delete_message()
            with open(banner, "rb") as f:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=f, caption=text,
                    parse_mode="Markdown", reply_markup=vip_kb,
                )
        else:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=vip_kb)
        return

    msg    = format_signal_message(signal)
    suffix = "\n\n_⚠️ Showing cached signal — live data temporarily unavailable._" if signal.get("_from_cache") else ""

    # Send with signal banner image
    banner = os.path.join(ASSETS_DIR, "signal_banner.png")
    if os.path.exists(banner):
        await query.delete_message()
        with open(banner, "rb") as f:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=f, caption=msg + suffix,
                parse_mode="Markdown", reply_markup=kb,
            )
    else:
        await query.edit_message_text(msg + suffix, parse_mode="Markdown", reply_markup=kb)
