"""Admin panel handler — triggered by ⚙️ Admin Panel keyboard button."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from admin import (
    is_admin, get_bot_stats, promote_user, demote_user, ban, unban,
    are_broadcasts_enabled, toggle_broadcasts,
    get_min_confidence, set_min_confidence,
    get_enabled_pairs, set_enabled_pairs,
)
from database import (
    get_all_payment_methods, add_payment_method, update_payment_method,
    delete_payment_method, get_pending_payments, get_recent_signals,
    get_all_settings, set_setting,
)
from payments import approve_payment, reject_payment
from broadcast import broadcast_message
from config import SUPPORTED_PAIRS, SUBSCRIPTION_PLANS

logger = logging.getLogger(__name__)


def _admin_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistics",        callback_data="adm_stats")],
        [InlineKeyboardButton("📢 Broadcast",         callback_data="adm_broadcast_menu")],
        [InlineKeyboardButton("👥 Manage Users",      callback_data="adm_users")],
        [InlineKeyboardButton("💳 Payment Methods",   callback_data="adm_payment_methods")],
        [InlineKeyboardButton("⏳ Pending Payments",  callback_data="adm_pending_payments")],
        [InlineKeyboardButton("📡 Recent Signals",    callback_data="adm_signals")],
        [InlineKeyboardButton("⚙️ Bot Settings",      callback_data="adm_settings")],
        [InlineKeyboardButton("🔙 Close",             callback_data="close_inline")],
    ])


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered by ⚙️ Admin Panel keyboard button."""
    user = update.effective_user
    if not is_admin(user.id):
        return
    await update.message.reply_text(
        "🛡️ *Admin Panel*\n\nSelect an option:",
        parse_mode="Markdown",
        reply_markup=_admin_main_kb(),
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = update.effective_user
    if not is_admin(user.id):
        await query.answer("❌ Unauthorised.", show_alert=True)
        return
    await query.answer()
    data = query.data

    # ── back ──────────────────────────────────────────────────────────────────
    if data == "adm_back":
        await query.edit_message_text(
            "🛡️ *Admin Panel*\n\nSelect an option:",
            parse_mode="Markdown", reply_markup=_admin_main_kb(),
        )

    # ── statistics ────────────────────────────────────────────────────────────
    elif data == "adm_stats":
        s    = get_bot_stats()
        sigs = get_recent_signals(limit=5)
        sig_lines = ""
        for sg in sigs:
            e = "🟢" if sg["direction"]=="BUY" else "🔴"
            sig_lines += f"\n{e} {sg['pair']} | {sg['timeframe']} | {sg['confidence']}%"
        text = (
            f"📊 *Bot Statistics*\n\n"
            f"👥 Total Users: `{s['total']}`\n"
            f"👑 VIP Users:   `{s['vip']}`\n"
            f"📅 Active Today:`{s['active_today']}`\n\n"
            f"📡 *Last Signals:*{sig_lines or ' None yet'}"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_back")]])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

    # ── broadcast menu ────────────────────────────────────────────────────────
    elif data == "adm_broadcast_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Broadcast ALL Users",  callback_data="adm_broadcast_all")],
            [InlineKeyboardButton("👑 Broadcast VIP Only",   callback_data="adm_broadcast_vip")],
            [InlineKeyboardButton("🔙 Back",                 callback_data="adm_back")],
        ])
        await query.edit_message_text("📢 *Broadcast*\nChoose target:", parse_mode="Markdown", reply_markup=kb)

    elif data in ("adm_broadcast_all", "adm_broadcast_vip"):
        context.user_data["adm_broadcast_target"] = "vip" if data == "adm_broadcast_vip" else "all"
        await query.edit_message_text(
            "📢 *Broadcast Message*\n\nType the message to send (Markdown supported):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]]),
        )

    # ── manage users ──────────────────────────────────────────────────────────
    elif data == "adm_users":
        context.user_data["adm_user_action"] = True
        await query.edit_message_text(
            "👥 *Manage Users*\n\nSend: `<user_id> <action>`\n\n"
            "Actions:\n`vip` · `devip` · `ban` · `unban`\n\n"
            "Example: `123456789 vip`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_back")]]),
        )

    # ── payment methods ───────────────────────────────────────────────────────
    elif data == "adm_payment_methods":
        methods = get_all_payment_methods()
        lines   = ["💳 *Payment Methods*\n"]
        for m in methods:
            lines.append(f"• `#{m['id']}` *{m['name']}*\n  `{m['details'][:50]}`")
        if not methods:
            lines.append("_No methods configured._")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add",    callback_data="adm_pm_add")],
            [InlineKeyboardButton("✏️ Edit",   callback_data="adm_pm_edit")],
            [InlineKeyboardButton("🗑️ Delete", callback_data="adm_pm_delete")],
            [InlineKeyboardButton("🔙 Back",   callback_data="adm_back")],
        ])
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb)

    elif data in ("adm_pm_add", "adm_pm_edit", "adm_pm_delete"):
        context.user_data["adm_pm_action"] = data.replace("adm_pm_", "")
        hints = {
            "add":    "Format: `NAME | DETAILS`\nExample: `USDT TRC20 | Wallet: TXxxxx`",
            "edit":   "Format: `ID | NEW_NAME | NEW_DETAILS`",
            "delete": "Send the method ID to delete.",
        }
        action = data.replace("adm_pm_", "")
        await query.edit_message_text(
            f"*{action.title()} Payment Method*\n\n{hints[action]}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_payment_methods")]]),
        )

    # ── pending payments ──────────────────────────────────────────────────────
    elif data == "adm_pending_payments":
        pending = get_pending_payments()
        if not pending:
            await query.edit_message_text(
                "✅ *No pending payments.*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_back")]]),
            )
            return
        text = "⏳ *Pending Payments:*\n\n"
        rows = []
        for p in pending[:10]:
            text += f"#{p['id']} | {p['first_name']} | {p['plan']} | `{p['transaction_id'][:20]}`\n"
            rows.append([
                InlineKeyboardButton(f"✅ #{p['id']}", callback_data=f"adm_approve_{p['id']}"),
                InlineKeyboardButton(f"❌ #{p['id']}", callback_data=f"adm_reject_{p['id']}"),
            ])
        rows.append([InlineKeyboardButton("🔙 Back", callback_data="adm_back")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("adm_approve_"):
        pid    = int(data.replace("adm_approve_", ""))
        result = approve_payment(pid, user.id)
        if result["success"]:
            try:
                await context.bot.send_message(
                    result["telegram_id"],
                    f"🎉 *Payment Approved!*\n\nYour *{result['plan'].upper()}* VIP is now active! 🚀",
                    parse_mode="Markdown",
                )
            except Exception:
                pass
            await query.edit_message_text(f"✅ Payment #{pid} approved — VIP activated.")
        else:
            await query.edit_message_text(f"❌ Error: {result['error']}")

    elif data.startswith("adm_reject_"):
        pid    = int(data.replace("adm_reject_", ""))
        result = reject_payment(pid, user.id)
        if result["success"]:
            try:
                await context.bot.send_message(
                    result["telegram_id"],
                    "❌ *Payment Rejected.*\n\nTransaction could not be verified. Please contact admin or resubmit.",
                    parse_mode="Markdown",
                )
            except Exception:
                pass
            await query.edit_message_text(f"❌ Payment #{pid} rejected.")
        else:
            await query.edit_message_text(f"❌ Error: {result['error']}")

    # ── recent signals ────────────────────────────────────────────────────────
    elif data == "adm_signals":
        sigs = get_recent_signals(limit=15)
        if not sigs:
            text = "📡 *No signals recorded yet.*"
        else:
            text = "📡 *Recent Signals:*\n\n"
            for s in sigs:
                e = "🟢" if s["direction"]=="BUY" else "🔴"
                text += f"{e} `{s['pair']}` | `{s['timeframe']}` | `{s['direction']}` | {s['confidence']}% | `{s['status']}`\n"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_back")]])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

    # ── settings ──────────────────────────────────────────────────────────────
    elif data == "adm_settings":
        conf    = get_min_confidence()
        pairs   = ", ".join(get_enabled_pairs())
        bc_on   = are_broadcasts_enabled()
        text = (
            f"⚙️ *Bot Settings*\n\n"
            f"🎯 Min Confidence:  `{conf}%`\n"
            f"📡 Enabled Pairs:   `{pairs}`\n"
            f"📢 VIP Broadcasts:  `{'ON' if bc_on else 'OFF'}`\n"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🎯 Set Confidence ({conf}%)",   callback_data="adm_set_confidence")],
            [InlineKeyboardButton("📡 Toggle Pairs",                  callback_data="adm_toggle_pairs")],
            [InlineKeyboardButton(f"📢 Broadcasts: {'✅ ON' if bc_on else '❌ OFF'}", callback_data="adm_toggle_bc")],
            [InlineKeyboardButton("💰 VIP Plans Info",                callback_data="adm_vip_plans")],
            [InlineKeyboardButton("🔙 Back",                          callback_data="adm_back")],
        ])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

    elif data == "adm_toggle_bc":
        current = are_broadcasts_enabled()
        toggle_broadcasts(not current)
        await query.answer(f"Broadcasts {'disabled' if current else 'enabled'}.", show_alert=True)
        # Re-render settings
        conf  = get_min_confidence()
        pairs = ", ".join(get_enabled_pairs())
        bc_on = not current
        text  = (
            f"⚙️ *Bot Settings*\n\n"
            f"🎯 Min Confidence:  `{conf}%`\n"
            f"📡 Enabled Pairs:   `{pairs}`\n"
            f"📢 VIP Broadcasts:  `{'ON' if bc_on else 'OFF'}`\n"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🎯 Set Confidence ({conf}%)",   callback_data="adm_set_confidence")],
            [InlineKeyboardButton("📡 Toggle Pairs",                  callback_data="adm_toggle_pairs")],
            [InlineKeyboardButton(f"📢 Broadcasts: {'✅ ON' if bc_on else '❌ OFF'}", callback_data="adm_toggle_bc")],
            [InlineKeyboardButton("💰 VIP Plans Info",                callback_data="adm_vip_plans")],
            [InlineKeyboardButton("🔙 Back",                          callback_data="adm_back")],
        ])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

    elif data == "adm_set_confidence":
        context.user_data["adm_set_conf"] = True
        conf = get_min_confidence()
        await query.edit_message_text(
            f"🎯 *Set Minimum Confidence*\n\n"
            f"Current: `{conf}%`\n\n"
            f"Send a number between 50 and 99.\n"
            f"_Recommended: 75–85_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="adm_settings")]]),
        )

    elif data == "adm_toggle_pairs":
        enabled = get_enabled_pairs()
        rows    = []
        for p in SUPPORTED_PAIRS:
            tick = "✅" if p in enabled else "⬜"
            rows.append([InlineKeyboardButton(f"{tick} {p}", callback_data=f"adm_togglepair_{p}")])
        rows.append([InlineKeyboardButton("🔙 Back", callback_data="adm_settings")])
        await query.edit_message_text(
            "📡 *Toggle Enabled Pairs*\n\nTap a pair to enable/disable:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows),
        )

    elif data.startswith("adm_togglepair_"):
        pair    = data.replace("adm_togglepair_", "")
        enabled = get_enabled_pairs()
        if pair in enabled:
            enabled.remove(pair)
        else:
            enabled.append(pair)
        set_enabled_pairs(enabled)
        # Re-render
        rows = []
        for p in SUPPORTED_PAIRS:
            tick = "✅" if p in enabled else "⬜"
            rows.append([InlineKeyboardButton(f"{tick} {p}", callback_data=f"adm_togglepair_{p}")])
        rows.append([InlineKeyboardButton("🔙 Back", callback_data="adm_settings")])
        await query.edit_message_text(
            "📡 *Toggle Enabled Pairs*\n\nTap a pair to enable/disable:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows),
        )

    elif data == "adm_vip_plans":
        from config import SUBSCRIPTION_PLANS
        lines = ["💰 *VIP Subscription Plans*\n"]
        for k, p in SUBSCRIPTION_PLANS.items():
            lines.append(f"• *{p['name']}* — `{p['days']} days` (key: `{k}`)")
        lines.append("\n_Plans are configured in config.py_")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_settings")]])
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb)


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle free-text inputs from admin (broadcast, user management, settings)."""
    user = update.effective_user
    if not is_admin(user.id):
        return
    text = update.message.text.strip()

    # Broadcast
    target = context.user_data.pop("adm_broadcast_target", None)
    if target:
        vip_only = target == "vip"
        sent, failed = await broadcast_message(context.bot, text, vip_only=vip_only)
        await update.message.reply_text(
            f"✅ Broadcast {'(VIP) ' if vip_only else ''}sent: *{sent}* delivered, *{failed}* failed.",
            parse_mode="Markdown",
        )
        return

    # Set confidence
    if context.user_data.pop("adm_set_conf", None):
        try:
            val = int(text)
            set_min_confidence(val)
            val = get_min_confidence()
            await update.message.reply_text(f"✅ Minimum confidence set to `{val}%`.", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ Please send a number between 50 and 99.")
        return

    # User management
    if context.user_data.pop("adm_user_action", None):
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ Format: `<user_id> <action>`", parse_mode="Markdown")
            return
        try:
            uid    = int(parts[0])
            action = parts[1].lower()
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")
            return
        actions = {
            "vip":   (promote_user, "✅ VIP granted."),
            "devip": (demote_user,  "✅ VIP removed."),
            "ban":   (ban,          "🚫 User banned."),
            "unban": (unban,        "✅ User unbanned."),
        }
        if action not in actions:
            await update.message.reply_text("❌ Unknown action: vip / devip / ban / unban")
            return
        fn, msg = actions[action]
        fn(uid)
        await update.message.reply_text(msg)
        if action == "vip":
            try:
                await context.bot.send_message(uid, "🎉 You have been granted VIP access by the admin!")
            except Exception:
                pass
        return

    # Payment method management
    pm_action = context.user_data.pop("adm_pm_action", None)
    if pm_action:
        if pm_action == "add":
            parts = [p.strip() for p in text.split("|", 1)]
            if len(parts) != 2:
                await update.message.reply_text("❌ Format: `NAME | DETAILS`", parse_mode="Markdown")
                return
            add_payment_method(parts[0], parts[1])
            await update.message.reply_text(f"✅ Payment method *{parts[0]}* added.", parse_mode="Markdown")
        elif pm_action == "edit":
            parts = [p.strip() for p in text.split("|", 2)]
            if len(parts) != 3:
                await update.message.reply_text("❌ Format: `ID | NAME | DETAILS`", parse_mode="Markdown")
                return
            try:
                mid = int(parts[0])
            except ValueError:
                await update.message.reply_text("❌ Invalid ID.")
                return
            update_payment_method(mid, parts[1], parts[2])
            await update.message.reply_text(f"✅ Method #{mid} updated.")
        elif pm_action == "delete":
            try:
                mid = int(text)
            except ValueError:
                await update.message.reply_text("❌ Invalid ID.")
                return
            delete_payment_method(mid)
            await update.message.reply_text(f"✅ Method #{mid} deleted.")
        return
