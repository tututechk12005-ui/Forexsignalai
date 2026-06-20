import sqlite3
import logging
from datetime import datetime, timedelta
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE NOT NULL,
            username    TEXT,
            first_name  TEXT,
            last_name   TEXT,
            is_vip      INTEGER DEFAULT 0,
            is_banned   INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            last_active TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS admins (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            added_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            plan        TEXT NOT NULL,
            start_date  TEXT NOT NULL,
            end_date    TEXT NOT NULL,
            is_active   INTEGER DEFAULT 1,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS payment_methods (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            details    TEXT NOT NULL,
            is_active  INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS payments (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id       INTEGER NOT NULL,
            plan              TEXT NOT NULL,
            payment_method_id INTEGER NOT NULL,
            transaction_id    TEXT NOT NULL,
            status            TEXT DEFAULT 'pending',
            submitted_at      TEXT DEFAULT (datetime('now')),
            reviewed_at       TEXT,
            reviewed_by       INTEGER,
            FOREIGN KEY (telegram_id)       REFERENCES users(telegram_id),
            FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id)
        );

        CREATE TABLE IF NOT EXISTS signals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            pair         TEXT NOT NULL,
            timeframe    TEXT NOT NULL,
            direction    TEXT NOT NULL,
            entry        REAL,
            stop_loss    REAL,
            take_profit1 REAL,
            take_profit2 REAL,
            take_profit3 REAL,
            risk_reward  REAL,
            confidence   INTEGER,
            bos          INTEGER DEFAULT 0,
            choch        INTEGER DEFAULT 0,
            liquidity    INTEGER DEFAULT 0,
            order_block  INTEGER DEFAULT 0,
            fvg          INTEGER DEFAULT 0,
            trend_ok     INTEGER DEFAULT 0,
            status       TEXT DEFAULT 'active',
            notified_tp1 INTEGER DEFAULT 0,
            notified_sl  INTEGER DEFAULT 0,
            generated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        INSERT OR IGNORE INTO settings (key, value) VALUES
            ('vip_signal_broadcast', '1'),
            ('auto_scan_enabled',    '1'),
            ('min_confidence',       '80'),
            ('bot_maintenance',      '0'),
            ('enabled_pairs',        'EURUSD,GBPUSD,USDJPY,GBPJPY,XAUUSD,BTCUSD'),
            ('scan_interval_min',    '15');
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialised.")


# ── users ──────────────────────────────────────────────────────────────────────

def upsert_user(telegram_id, username, first_name, last_name):
    conn = get_connection()
    conn.execute("""
        INSERT INTO users (telegram_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username    = excluded.username,
            first_name  = excluded.first_name,
            last_name   = excluded.last_name,
            last_active = datetime('now')
    """, (telegram_id, username, first_name, last_name))
    conn.commit()
    conn.close()


def get_user(telegram_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users WHERE is_banned=0").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_vip_users():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users WHERE is_vip=1 AND is_banned=0").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_vip(telegram_id, is_vip: bool):
    conn = get_connection()
    conn.execute("UPDATE users SET is_vip=? WHERE telegram_id=?", (int(is_vip), telegram_id))
    conn.commit()
    conn.close()


def ban_user(telegram_id, banned: bool):
    conn = get_connection()
    conn.execute("UPDATE users SET is_banned=? WHERE telegram_id=?", (int(banned), telegram_id))
    conn.commit()
    conn.close()


def count_users():
    conn = get_connection()
    total        = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    vip          = conn.execute("SELECT COUNT(*) FROM users WHERE is_vip=1").fetchone()[0]
    active_today = conn.execute("SELECT COUNT(*) FROM users WHERE last_active >= date('now')").fetchone()[0]
    conn.close()
    return {"total": total, "vip": vip, "active_today": active_today}


# ── subscriptions ──────────────────────────────────────────────────────────────

def add_subscription(telegram_id, plan, days):
    conn = get_connection()
    now = datetime.utcnow()
    end = now + timedelta(days=days)
    conn.execute("""
        INSERT INTO subscriptions (telegram_id, plan, start_date, end_date)
        VALUES (?, ?, ?, ?)
    """, (telegram_id, plan, now.isoformat(), end.isoformat()))
    conn.execute("UPDATE users SET is_vip=1 WHERE telegram_id=?", (telegram_id,))
    conn.commit()
    conn.close()


def get_active_subscription(telegram_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM subscriptions
        WHERE telegram_id=? AND is_active=1 AND end_date >= datetime('now')
        ORDER BY end_date DESC LIMIT 1
    """, (telegram_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def expire_subscriptions():
    conn = get_connection()
    conn.execute("""
        UPDATE subscriptions SET is_active=0
        WHERE is_active=1 AND end_date < datetime('now')
    """)
    expired = conn.execute("""
        SELECT DISTINCT telegram_id FROM subscriptions WHERE is_active=0
    """).fetchall()
    for row in expired:
        active = conn.execute("""
            SELECT id FROM subscriptions WHERE telegram_id=? AND is_active=1
        """, (row[0],)).fetchone()
        if not active:
            conn.execute("UPDATE users SET is_vip=0 WHERE telegram_id=?", (row[0],))
    conn.commit()
    conn.close()


# ── payment methods ────────────────────────────────────────────────────────────

def get_all_payment_methods():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM payment_methods WHERE is_active=1").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_payment_method(name, details):
    conn = get_connection()
    conn.execute("INSERT INTO payment_methods (name, details) VALUES (?, ?)", (name, details))
    conn.commit()
    conn.close()


def update_payment_method(method_id, name, details):
    conn = get_connection()
    conn.execute("UPDATE payment_methods SET name=?, details=? WHERE id=?", (name, details, method_id))
    conn.commit()
    conn.close()


def delete_payment_method(method_id):
    conn = get_connection()
    conn.execute("UPDATE payment_methods SET is_active=0 WHERE id=?", (method_id,))
    conn.commit()
    conn.close()


# ── payments ───────────────────────────────────────────────────────────────────

def submit_payment(telegram_id, plan, method_id, txn_id):
    conn = get_connection()
    conn.execute("""
        INSERT INTO payments (telegram_id, plan, payment_method_id, transaction_id)
        VALUES (?, ?, ?, ?)
    """, (telegram_id, plan, method_id, txn_id))
    conn.commit()
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return pid


def get_pending_payments():
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.*, u.username, u.first_name, pm.name as method_name
        FROM payments p
        JOIN users u  ON p.telegram_id       = u.telegram_id
        JOIN payment_methods pm ON p.payment_method_id = pm.id
        WHERE p.status='pending'
        ORDER BY p.submitted_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_payment(payment_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT p.*, u.username, u.first_name, pm.name as method_name
        FROM payments p
        JOIN users u  ON p.telegram_id       = u.telegram_id
        JOIN payment_methods pm ON p.payment_method_id = pm.id
        WHERE p.id=?
    """, (payment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def review_payment(payment_id, status, admin_id):
    conn = get_connection()
    conn.execute("""
        UPDATE payments SET status=?, reviewed_at=datetime('now'), reviewed_by=?
        WHERE id=?
    """, (status, admin_id, payment_id))
    conn.commit()
    conn.close()


# ── signals ────────────────────────────────────────────────────────────────────

def save_signal(pair, timeframe, direction, entry, stop_loss,
                tp1, tp2, tp3, rr, confidence, flags):
    conn = get_connection()
    conn.execute("""
        INSERT INTO signals
        (pair, timeframe, direction, entry, stop_loss,
         take_profit1, take_profit2, take_profit3,
         risk_reward, confidence,
         bos, choch, liquidity, order_block, fvg, trend_ok)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        pair, timeframe, direction, entry, stop_loss,
        tp1, tp2, tp3, rr, confidence,
        int(flags.get("bos",         False)),
        int(flags.get("choch",       False)),
        int(flags.get("liquidity",   False)),
        int(flags.get("order_block", False)),
        int(flags.get("fvg",         False)),
        int(flags.get("trend_ok",    False)),
    ))
    conn.commit()
    sig_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return sig_id


def get_latest_signal(pair):
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM signals WHERE pair=?
        ORDER BY generated_at DESC LIMIT 1
    """, (pair,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_recent_signals(limit=20):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM signals ORDER BY generated_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_active_signals_for_tracking():
    """Return all signals that are still 'active' and not yet fully notified."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM signals
        WHERE status='active'
          AND generated_at >= datetime('now', '-24 hours')
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_signal_tp1(signal_id):
    conn = get_connection()
    conn.execute("""
        UPDATE signals SET status='tp1_hit', notified_tp1=1 WHERE id=?
    """, (signal_id,))
    conn.commit()
    conn.close()


def mark_signal_sl(signal_id):
    conn = get_connection()
    conn.execute("""
        UPDATE signals SET status='sl_hit', notified_sl=1 WHERE id=?
    """, (signal_id,))
    conn.commit()
    conn.close()


# ── settings ───────────────────────────────────────────────────────────────────

def get_setting(key, default=""):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key, value):
    conn = get_connection()
    conn.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')
    """, (key, value))
    conn.commit()
    conn.close()


def get_all_settings():
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}
