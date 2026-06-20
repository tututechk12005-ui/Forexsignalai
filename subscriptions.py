"""Subscription management."""
import logging
from database import add_subscription, get_active_subscription, expire_subscriptions
from config import SUBSCRIPTION_PLANS

logger = logging.getLogger(__name__)


def activate_subscription(telegram_id: int, plan_key: str):
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        raise ValueError(f"Unknown plan: {plan_key}")
    add_subscription(telegram_id, plan_key, plan["days"])
    logger.info("Activated %s for user %d", plan_key, telegram_id)


def check_subscription(telegram_id: int) -> dict:
    sub = get_active_subscription(telegram_id)
    if sub:
        return {"active": True, "plan": sub["plan"], "end_date": sub["end_date"]}
    return {"active": False}


def run_expiry_check():
    expire_subscriptions()
    logger.info("Subscription expiry check done.")
