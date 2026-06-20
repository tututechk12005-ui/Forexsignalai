"""Admin utilities."""
import logging
from config import ADMIN_ID
from database import set_vip, ban_user, count_users, get_setting, set_setting

logger = logging.getLogger(__name__)


def is_admin(telegram_id: int) -> bool:
    return telegram_id == ADMIN_ID


def get_bot_stats() -> dict:
    return count_users()


def promote_user(telegram_id: int):
    set_vip(telegram_id, True)
    logger.info("User %d → VIP", telegram_id)


def demote_user(telegram_id: int):
    set_vip(telegram_id, False)
    logger.info("User %d VIP removed", telegram_id)


def ban(telegram_id: int):
    ban_user(telegram_id, True)
    logger.info("User %d banned", telegram_id)


def unban(telegram_id: int):
    ban_user(telegram_id, False)
    logger.info("User %d unbanned", telegram_id)


def is_maintenance() -> bool:
    return get_setting("bot_maintenance", "0") == "1"


def toggle_maintenance(enabled: bool):
    set_setting("bot_maintenance", "1" if enabled else "0")


def are_broadcasts_enabled() -> bool:
    return get_setting("vip_signal_broadcast", "1") == "1"


def toggle_broadcasts(enabled: bool):
    set_setting("vip_signal_broadcast", "1" if enabled else "0")


def get_min_confidence() -> int:
    return int(get_setting("min_confidence", "80"))


def set_min_confidence(value: int):
    value = max(50, min(99, value))
    set_setting("min_confidence", str(value))
    logger.info("min_confidence → %d", value)


def get_enabled_pairs() -> list:
    from config import SUPPORTED_PAIRS
    raw = get_setting("enabled_pairs", ",".join(SUPPORTED_PAIRS))
    return [p.strip() for p in raw.split(",") if p.strip()]


def set_enabled_pairs(pairs: list):
    set_setting("enabled_pairs", ",".join(pairs))
