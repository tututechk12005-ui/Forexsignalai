"""Start handler — main menu with persistent ReplyKeyboardMarkup."""
import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import upsert_user, get_user
from admin import is_admin, is_maintenance
from utils.helpers import is_forex_market_closed
from config import ASSETS_DIR

logger = logging.getLogger(__name__)

# ── keyboard layouts ──────────────────────────────────────────────────────────

USER_KB = ReplyKeyboardMarkup(
    [
        ["📊 Select Pair", "📈 Get Signal"],
        ["💳 Subscription", "💰 Payment"],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

ADMIN_KB = ReplyKeyboardMarkup(
    [
        ["📊 Select Pair", "📈 Get Signal"],
        ["💳 Subscription", "💰 Payment"],
        ["⚙️ Admin Panel"],
    ],
    resize_keyboard=True,
    is_persistent=True,
)


def get_keyboard(telegram_id: int) -> ReplyKeyboardMarkup:
    return ADMIN_KB if is_admin(telegram_id) else USER_KB


WELCOME_TEXT = (
    "👋 *Welcome to Forex SMC Signal Bot!*\n\n"
    "📊 Powered by *Smart Money Concepts (SMC)*\n\n"
    "🔍 *What I analyse:*\n"
    "• Break of Structure (BOS)\n"
    "• Change of Character (CHoCH)\n"
    "• Liquidity Sweep Detection\n"
    "• Order Block Analysis\n"
    "• Fair Value Gap (FVG)\n"
    "• EMA Trend Confirmation\n"
    "• Multi-Timeframe Analysis\n\n"
    "🎯 *Pairs:* EURUSD · GBPUSD · USDJPY · GBPJPY · XAUUSD · BTCUSD\n\n"
    "Use the buttons below to get started 👇"
)


async def _send_welcome(update: Update, telegram_id: int):
    kb = get_keyboard(telegram_id)
    banner = os.path.join(ASSETS_DIR, "welcome_banner.png")
    if os.path.exists(banner):
        with open(banner, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption=WELCOME_TEXT,
                parse_mode="Markdown",
                reply_markup=kb,
            )
    else:
        await update.message.reply_text(
            WELCOME_TEXT,
            parse_mode="Markdown",
            reply_markup=kb,
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    upsert_user(
        telegram_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        last_name=user.last_name or "",
    )
    if is_maintenance() and not is_admin(user.id):
        await update.message.reply_text(
            "🔧 *Bot is under maintenance.*\nPlease try again later.",
            parse_mode="Markdown",
        )
        return
    await _send_welcome(update, user.id)


async def my_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user    = update.effective_user
    db_user = get_user(user.id)
    if not db_user:
        await query.edit_message_text("❌ User not found. Please use /start.")
        return
    from database import get_active_subscription
    from utils.helpers import days_until
    sub    = get_active_subscription(user.id)
    status = "👑 VIP" if db_user.get("is_vip") else "🆓 Free"
    sub_info = ""
    if sub:
        dl = days_until(sub["end_date"])
        sub_info = f"\n📦 Plan: *{sub['plan'].upper()}*\n⏳ Expires in: *{dl} days*"
    name = f"{db_user.get('first_name','')}{' ' + db_user.get('last_name','') if db_user.get('last_name') else ''}".strip()
    text = (
        f"👤 *My Account*\n\n"
        f"Name: `{name}`\n"
        f"Username: @{db_user.get('username') or 'N/A'}\n"
        f"ID: `{user.id}`\n"
        f"Status: {status}"
        f"{sub_info}\n\n"
        f"🕒 Member since: `{db_user.get('created_at','N/A')[:10]}`"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Close", callback_data="close_inline")]])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)


async def close_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.delete_message()
