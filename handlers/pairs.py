"""Pair selection handler."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_setting
from config import SUPPORTED_PAIRS
from utils.helpers import is_pair_tradeable, is_forex_market_closed

logger = logging.getLogger(__name__)

PAIR_DESC = {
    "EURUSD": "🇪🇺 EUR/USD — Euro / US Dollar",
    "GBPUSD": "🇬🇧 GBP/USD — Pound / US Dollar",
    "USDJPY": "🇺🇸 USD/JPY — Dollar / Japanese Yen",
    "GBPJPY": "🇬🇧 GBP/JPY — Pound / Japanese Yen",
    "XAUUSD": "🥇 XAU/USD — Gold / US Dollar",
    "BTCUSD": "₿ BTC/USD — Bitcoin / US Dollar",
}


def _pairs_keyboard() -> InlineKeyboardMarkup:
    enabled_raw = get_setting("enabled_pairs", ",".join(SUPPORTED_PAIRS))
    enabled     = [p.strip() for p in enabled_raw.split(",") if p.strip()]
    rows = []
    for pair in enabled:
        desc   = PAIR_DESC.get(pair, pair)
        closed = not is_pair_tradeable(pair)
        label  = f"{desc} 🔴" if closed else desc
        rows.append([InlineKeyboardButton(label, callback_data=f"pair_{pair}")])
    rows.append([InlineKeyboardButton("🔙 Close", callback_data="close_inline")])
    return InlineKeyboardMarkup(rows)


async def select_pair_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    market_note = ""
    if is_forex_market_closed():
        market_note = (
            "\n\n🔴 *Market Closed*\n"
            "Forex market is currently closed.\n"
            "Crypto pairs (XAU, BTC) remain available."
        )
    msg = await update.message.reply_text(
        f"📊 *Select a Trading Pair*\n\nChoose which pair to analyse:{market_note}",
        parse_mode="Markdown",
        reply_markup=_pairs_keyboard(),
    )


async def pair_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.replace("pair_", "")
    if pair not in SUPPORTED_PAIRS:
        await query.answer("❌ Invalid pair.", show_alert=True)
        return
    context.user_data["selected_pair"] = pair
    if not is_pair_tradeable(pair):
        await query.edit_message_text(
            f"🔴 *Market Closed — {pair}*\n\n"
            "Forex market is currently closed (Saturday/Sunday).\n"
            "No new signals available for this pair.\n\n"
            "✅ Crypto pairs (XAUUSD, BTCUSD) continue to operate.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Pairs", callback_data="pairs_menu")],
            ]),
        )
        return
    desc = PAIR_DESC.get(pair, pair)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💡 Get Signal Now", callback_data=f"signal_{pair}")],
        [InlineKeyboardButton("📊 Select Another Pair", callback_data="pairs_menu")],
        [InlineKeyboardButton("🔙 Close", callback_data="close_inline")],
    ])
    await query.edit_message_text(
        f"✅ *Selected: {desc}*\n\nPress *Get Signal Now* to run SMC analysis across 15m · 1H · 4H.",
        parse_mode="Markdown",
        reply_markup=kb,
    )


async def pairs_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    market_note = ""
    if is_forex_market_closed():
        market_note = (
            "\n\n🔴 *Market Closed*\n"
            "Forex market is currently closed.\n"
            "Crypto pairs remain available."
        )
    await query.edit_message_text(
        f"📊 *Select a Trading Pair*\n\nChoose which pair to analyse:{market_note}",
        parse_mode="Markdown",
        reply_markup=_pairs_keyboard(),
    )
