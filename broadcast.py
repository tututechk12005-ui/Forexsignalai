"""Broadcast utilities."""
import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError
from database import get_all_users, get_vip_users

logger = logging.getLogger(__name__)


async def broadcast_message(bot: Bot, message: str, vip_only: bool = False, parse_mode: str = "Markdown"):
    users   = get_vip_users() if vip_only else get_all_users()
    success = failed = 0
    for user in users:
        try:
            await bot.send_message(chat_id=user["telegram_id"], text=message, parse_mode=parse_mode)
            success += 1
            await asyncio.sleep(0.05)
        except TelegramError as e:
            logger.warning("Broadcast failed → %d: %s", user["telegram_id"], e)
            failed += 1
    logger.info("Broadcast done: %d sent / %d failed", success, failed)
    return success, failed


async def broadcast_signal(bot: Bot, signal_text: str):
    return await broadcast_message(bot, signal_text, vip_only=True)
