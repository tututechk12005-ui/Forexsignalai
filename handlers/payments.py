"""Payment and subscription flow handlers."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_all_payment_methods, get_user, get_active_subscription
from payments import process_payment_submission
from utils.helpers import days_until, plan_display_name
from config import SUBSCRIPTION_PLANS, ADMIN_ID

logger = logging.getLogger(__name__)


def _plans_keyboard():
    rows = [
        [InlineKeyboardButton(f"📦 {p['name']}", callback_data=f"buyplan_{k}")]
        for k, p in SUBSCRIPTION_PLANS.items()
    ]
    rows.append([InlineKeyboardButton("🔙 Close", callback_data="close_inline")])
    return InlineKeyboardMarkup(rows)


async def subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered by 💳 Subscription button."""
    user    = update.effective_user
    db_user = get_user(user.id)
    sub     = get_active_subscription(user.id)

    if sub:
        dl     = days_until(sub["end_date"])
        status = (
            f"✅ *Active VIP Subscription*\n\n"
            f"📦 Plan: `{sub['plan'].upper()}`\n"
            f"⏳ Days remaining: *{dl}*\n"
            f"📅 Expires: `{sub['end_date'][:10]}`"
        )
    elif db_user and db_user.get("is_vip"):
        status = "👑 *VIP Access* (granted by admin)"
    else:
        status = (
            "🆓 *Free Account*\n\n"
            "🔓 Upgrade to VIP for:\n"
            "• Full Entry · SL · TP levels\n"
            "• Auto-broadcast alerts\n"
            "• TP1 / SL hit notifications\n"
            "• High-confidence signals\n"
            "• Priority support"
        )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Buy Subscription", callback_data="buy_sub_plans")],
        [InlineKeyboardButton("👤 My Account",       callback_data="my_account_inline")],
        [InlineKeyboardButton("🔙 Close",            callback_data="close_inline")],
    ])
    await update.message.reply_text(status, parse_mode="Markdown", reply_markup=kb)


async def payment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered by 💰 Payment button."""
    user    = update.effective_user
    db_user = get_user(user.id)

    if db_user and db_user.get("is_vip"):
        sub = get_active_subscription(user.id)
        dl  = days_until(sub["end_date"]) if sub else 0
        await update.message.reply_text(
            f"✅ *You have an active VIP subscription!*\n\n⏳ Expires in: *{dl} days*\n\nThank you for your support! 🙏",
            parse_mode="Markdown",
        )
        return

    methods = get_all_payment_methods()
    if not methods:
        await update.message.reply_text(
            "⚠️ No payment methods configured yet.\nPlease contact the admin.",
        )
        return

    await update.message.reply_text(
        "💳 *Purchase a VIP Subscription*\n\nSelect a plan:",
        parse_mode="Markdown",
        reply_markup=_plans_keyboard(),
    )


# ── inline callbacks ──────────────────────────────────────────────────────────

async def buy_sub_plans_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    methods = get_all_payment_methods()
    if not methods:
        await query.edit_message_text("⚠️ No payment methods configured. Contact admin.")
        return
    await query.edit_message_text(
        "💳 *Select a Subscription Plan:*",
        parse_mode="Markdown",
        reply_markup=_plans_keyboard(),
    )


async def plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    plan_key = query.data.replace("buyplan_", "")
    if plan_key not in SUBSCRIPTION_PLANS:
        await query.answer("❌ Invalid plan.", show_alert=True)
        return
    context.user_data["payment_plan"] = plan_key
    methods = get_all_payment_methods()
    if not methods:
        await query.edit_message_text("⚠️ No payment methods available.")
        return
    rows = [
        [InlineKeyboardButton(m["name"], callback_data=f"paymethod_{m['id']}")]
        for m in methods
    ]
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="buy_sub_plans")])
    plan = SUBSCRIPTION_PLANS[plan_key]
    await query.edit_message_text(
        f"✅ Plan: *{plan['name']}*\n\nChoose a payment method:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await query.answer()
    method_id = int(query.data.replace("paymethod_", ""))
    context.user_data["payment_method_id"] = method_id
    methods   = get_all_payment_methods()
    method    = next((m for m in methods if m["id"] == method_id), None)
    if not method:
        await query.answer("❌ Payment method not found.", show_alert=True)
        return
    context.user_data["awaiting_txn"] = True
    await query.edit_message_text(
        f"💳 *Payment Method: {method['name']}*\n\n"
        f"📋 *Details:*\n`{method['details']}`\n\n"
        f"📝 Complete your payment then reply with your *Transaction ID / Reference Number*.\n\n"
        "_Type your transaction ID now:_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="close_inline")]]),
    )


async def my_account_inline_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user    = update.effective_user
    db_user = get_user(user.id)
    if not db_user:
        await query.edit_message_text("❌ User not found.")
        return
    sub    = get_active_subscription(user.id)
    status = "👑 VIP" if db_user.get("is_vip") else "🆓 Free"
    sub_info = ""
    if sub:
        dl = days_until(sub["end_date"])
        sub_info = f"\n📦 Plan: *{sub['plan'].upper()}*\n⏳ Expires in: *{dl} days*"
    name = f"{db_user.get('first_name','')} {db_user.get('last_name','') or ''}".strip()
    text = (
        f"👤 *My Account*\n\n"
        f"Name: `{name}`\n"
        f"Username: @{db_user.get('username') or 'N/A'}\n"
        f"ID: `{user.id}`\n"
        f"Status: {status}{sub_info}\n\n"
        f"🕒 Since: `{db_user.get('created_at','N/A')[:10]}`"
    )
    await query.edit_message_text(text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Close", callback_data="close_inline")]]))


async def receive_txn_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle transaction ID text submitted by a non-admin user."""
    if not context.user_data.get("awaiting_txn"):
        return
    txn_id   = update.message.text.strip()
    if not txn_id or len(txn_id) < 3:
        await update.message.reply_text("❌ Invalid transaction ID. Please try again.")
        return
    plan_key  = context.user_data.get("payment_plan")
    method_id = context.user_data.get("payment_method_id")
    if not plan_key or not method_id:
        await update.message.reply_text("❌ Session expired. Please use /start.")
        context.user_data.clear()
        return
    user = update.effective_user
    try:
        pid = process_payment_submission(user.id, plan_key, method_id, txn_id)
    except Exception as e:
        logger.error("Payment submission error: %s", e)
        await update.message.reply_text("❌ Failed to submit. Please try again.")
        return
    context.user_data.clear()
    plan = SUBSCRIPTION_PLANS.get(plan_key, {})
    await update.message.reply_text(
        f"✅ *Payment Submitted!*\n\n"
        f"📦 Plan: *{plan.get('name', plan_key)}*\n"
        f"🔑 TXN ID: `{txn_id}`\n"
        f"🆔 Reference: `#{pid}`\n\n"
        "⏳ Awaiting admin approval (usually 1–24 hours).",
        parse_mode="Markdown",
    )
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🔔 *New Payment — #{pid}*\n\n"
                f"👤 {user.first_name} (@{user.username or 'N/A'})\n"
                f"🆔 ID: `{user.id}`\n"
                f"📦 Plan: `{plan_key}`\n"
                f"🔑 TXN: `{txn_id}`\n\n"
                "Open *Admin Panel → Pending Payments* to review."
            ),
            parse_mode="Markdown",
        )
    except Exception:
        pass
