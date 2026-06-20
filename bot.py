"""Main bot entry point — no /admin command; keyboard-driven UI."""
import logging
from time import time as _time
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters,
)
from config import BOT_TOKEN, ADMIN_ID, RATE_LIMIT_SECONDS
from database import init_db
from scheduler import start_scheduler, stop_scheduler
from handlers.start import start_command, my_account_callback, close_inline, get_keyboard
from handlers.pairs import select_pair_menu, pair_selected, pairs_menu_callback
from handlers.signals import get_signal_menu, get_signal_for_pair
from handlers.payments import (
    subscription_menu, payment_menu,
    buy_sub_plans_cb, plan_selected, method_selected,
    my_account_inline_cb, receive_txn_id,
)
from handlers.admin import admin_panel, admin_callback, admin_text_handler
from utils.logger import logger

_last_req: dict = {}


async def _rate_guard(update: Update, context, handler):
    if update.effective_user:
        uid = update.effective_user.id
        now = _time()
        if now - _last_req.get(uid, 0) < RATE_LIMIT_SECONDS and uid != ADMIN_ID:
            if update.callback_query:
                await update.callback_query.answer("⏳ Please slow down.", show_alert=False)
            return
        _last_req[uid] = now
    return await handler(update, context)


async def _error_handler(update, context):
    logger.error("Unhandled error: %s", context.error, exc_info=context.error)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ An unexpected error occurred. Please try again or use /start."
            )
    except Exception:
        pass


# ── keyboard button text filters ──────────────────────────────────────────────

def _text(t: str):
    return filters.TEXT & filters.Regex(f"^{t}$") & ~filters.COMMAND


def build_application() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_error_handler(_error_handler)

    # ── commands ──────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))

    # ── persistent keyboard buttons ───────────────────────────────────────────
    app.add_handler(MessageHandler(_text("📊 Select Pair"),   select_pair_menu))
    app.add_handler(MessageHandler(_text("📈 Get Signal"),    get_signal_menu))
    app.add_handler(MessageHandler(_text("💳 Subscription"),  subscription_menu))
    app.add_handler(MessageHandler(_text("💰 Payment"),       payment_menu))
    app.add_handler(MessageHandler(
        _text("⚙️ Admin Panel") & filters.User(ADMIN_ID),
        admin_panel,
    ))

    # ── inline callback queries ───────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(close_inline,          pattern="^close_inline$"))
    app.add_handler(CallbackQueryHandler(my_account_callback,   pattern="^my_account$"))  # kept for legacy
    app.add_handler(CallbackQueryHandler(my_account_inline_cb,  pattern="^my_account_inline$"))
    app.add_handler(CallbackQueryHandler(pairs_menu_callback,   pattern="^pairs_menu$"))
    app.add_handler(CallbackQueryHandler(pair_selected,         pattern="^pair_"))
    app.add_handler(CallbackQueryHandler(get_signal_for_pair,   pattern="^signal_"))
    app.add_handler(CallbackQueryHandler(buy_sub_plans_cb,      pattern="^buy_sub_plans$"))
    app.add_handler(CallbackQueryHandler(plan_selected,         pattern="^buyplan_"))
    app.add_handler(CallbackQueryHandler(method_selected,       pattern="^paymethod_"))
    app.add_handler(CallbackQueryHandler(subscription_menu,     pattern="^subscription_menu$"))

    # admin callbacks (adm_*)
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^adm_"))

    # ── text message handlers ─────────────────────────────────────────────────
    # Admin free-text (broadcast, user management, settings, payment methods)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID),
        admin_text_handler,
    ))
    # Non-admin free-text → transaction ID submission
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID),
        receive_txn_id,
    ))

    return app


async def post_init(application: Application):
    init_db()
    logger.info("Database initialised.")
    start_scheduler(application.bot)
    logger.info("Scheduler started.")


async def post_shutdown(application: Application):
    stop_scheduler()


def main():
    logger.info("Starting Forex SMC Signal Bot…")
    app = build_application()
    app.post_init     = post_init
    app.post_shutdown = post_shutdown
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
