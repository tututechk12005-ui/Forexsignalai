"""Payment processing."""
import logging
from database import submit_payment, review_payment, get_pending_payments, get_payment
from subscriptions import activate_subscription

logger = logging.getLogger(__name__)


def process_payment_submission(telegram_id, plan, method_id, txn_id):
    pid = submit_payment(telegram_id, plan, method_id, txn_id)
    logger.info("Payment #%d submitted — user %d plan %s", pid, telegram_id, plan)
    return pid


def approve_payment(payment_id, admin_id):
    payment = get_payment(payment_id)
    if not payment:
        return {"success": False, "error": "Payment not found"}
    if payment["status"] != "pending":
        return {"success": False, "error": f"Already {payment['status']}"}
    review_payment(payment_id, "approved", admin_id)
    try:
        activate_subscription(payment["telegram_id"], payment["plan"])
    except ValueError as e:
        return {"success": False, "error": str(e)}
    logger.info("Payment #%d approved by admin %d", payment_id, admin_id)
    return {"success": True, "telegram_id": payment["telegram_id"], "plan": payment["plan"]}


def reject_payment(payment_id, admin_id):
    payment = get_payment(payment_id)
    if not payment:
        return {"success": False, "error": "Payment not found"}
    if payment["status"] != "pending":
        return {"success": False, "error": f"Already {payment['status']}"}
    review_payment(payment_id, "rejected", admin_id)
    logger.info("Payment #%d rejected by admin %d", payment_id, admin_id)
    return {"success": True, "telegram_id": payment["telegram_id"]}


def list_pending_payments():
    return get_pending_payments()
