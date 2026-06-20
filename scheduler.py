"""APScheduler — market scan + signal tracker + expiry check."""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Bot
from signals import scan_all_pairs
from broadcast import broadcast_signal, broadcast_message
from subscriptions import run_expiry_check
from utils.helpers import format_signal_message, format_result_message
from utils.api import fetch_latest_price
from database import (
    get_setting, get_active_signals_for_tracking,
    mark_signal_tp1, mark_signal_sl
)
from config import SIGNAL_SCAN_INTERVAL, SIGNAL_TRACKER_INTERVAL

logger = logging.getLogger(__name__)
_scheduler = None


# ── jobs ──────────────────────────────────────────────────────────────────────

async def _run_market_scan(bot: Bot):
    if get_setting("auto_scan_enabled", "1") != "1":
        return
    logger.info("Running scheduled market scan…")
    try:
        signals = await scan_all_pairs()
        if not signals:
            logger.info("No high-quality signals this cycle.")
            return
        if get_setting("vip_signal_broadcast", "1") == "1":
            for sig in signals:
                msg = format_signal_message(sig)
                sent, failed = await broadcast_signal(bot, msg)
                logger.info("Signal broadcast %s: %d sent / %d failed", sig["pair"], sent, failed)
    except Exception as e:
        logger.exception("Market scan error: %s", e)


async def _run_signal_tracker(bot: Bot):
    """
    Check all active signals against current price.
    Notify VIP users when TP1 is hit or SL is hit.
    """
    active = get_active_signals_for_tracking()
    if not active:
        return
    logger.debug("Tracking %d active signal(s)…", len(active))
    for sig in active:
        try:
            price = await fetch_latest_price(sig["pair"])
            if price is None:
                continue
            direction = sig["direction"]
            tp1 = sig["take_profit1"]
            sl  = sig["stop_loss"]

            # TP1 hit check
            if not sig["notified_tp1"]:
                hit_tp1 = (direction == "BUY"  and price >= tp1) or \
                          (direction == "SELL" and price <= tp1)
                if hit_tp1:
                    mark_signal_tp1(sig["id"])
                    msg = format_result_message(sig, "tp1")
                    await broadcast_message(bot, msg, vip_only=True)
                    logger.info("TP1 hit — %s signal #%d", sig["pair"], sig["id"])
                    continue

            # SL hit check
            if not sig["notified_sl"]:
                hit_sl = (direction == "BUY"  and price <= sl) or \
                         (direction == "SELL" and price >= sl)
                if hit_sl:
                    mark_signal_sl(sig["id"])
                    msg = format_result_message(sig, "sl")
                    await broadcast_message(bot, msg, vip_only=True)
                    logger.info("SL hit — %s signal #%d", sig["pair"], sig["id"])
        except Exception as e:
            logger.error("Tracker error signal #%d: %s", sig.get("id"), e)


async def _run_expiry_check():
    try:
        run_expiry_check()
    except Exception as e:
        logger.exception("Expiry check error: %s", e)


# ── lifecycle ─────────────────────────────────────────────────────────────────

def start_scheduler(bot: Bot):
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _run_market_scan,
        trigger=IntervalTrigger(seconds=SIGNAL_SCAN_INTERVAL),
        args=[bot], id="market_scan", replace_existing=True, max_instances=1,
    )
    _scheduler.add_job(
        _run_signal_tracker,
        trigger=IntervalTrigger(seconds=SIGNAL_TRACKER_INTERVAL),
        args=[bot], id="signal_tracker", replace_existing=True, max_instances=1,
    )
    _scheduler.add_job(
        _run_expiry_check,
        trigger=IntervalTrigger(hours=6),
        id="expiry_check", replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — scan every %ds, tracker every %ds.",
                SIGNAL_SCAN_INTERVAL, SIGNAL_TRACKER_INTERVAL)
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
