# 📊 Forex SMC Signal Bot v2

Production-ready Telegram bot delivering Smart Money Concept (SMC) forex signals
via Twelve Data API, with full admin panel, payment system, subscriptions, and
live TP/SL result tracking.

---

## What's New in v2

| Feature | Details |
|---------|---------|
| **Persistent keyboard** | ReplyKeyboardMarkup always visible at the bottom |
| **Admin panel via keyboard** | ⚙️ Admin Panel button — admin-only, invisible to users |
| **Market closure detection** | Weekends → no fake forex signals; crypto runs 24/7 |
| **Signal tracker** | Auto-detects TP1 hit / SL hit and notifies VIP users |
| **TP3 added** | Signals now have three take-profit levels |
| **EMA trend filter** | Extra SMC confluence layer via EMA20/50 alignment |
| **GBPJPY added** | 6 pairs total |
| **Admin settings** | Confidence threshold, enabled pairs, broadcast toggle |
| **Banner images** | Auto-sent with signals, welcome, and VIP upgrade prompts |

---

## Supported Pairs

| Pair | Type | Market Hours |
|------|------|--------------|
| EURUSD | Forex | Mon–Fri |
| GBPUSD | Forex | Mon–Fri |
| USDJPY | Forex | Mon–Fri |
| GBPJPY | Forex | Mon–Fri |
| XAUUSD | Gold  | 24/7 |
| BTCUSD | Crypto | 24/7 |

---

## SMC Engine

Each signal passes a multi-layer scoring system:

| Confluence Factor | Score |
|-------------------|-------|
| Break of Structure (BOS) | 3 pts |
| Change of Character (CHoCH) | 3 pts |
| EMA Trend Confirmation | 3 pts |
| Liquidity Sweep | 2 pts |
| Order Block | 2 pts |
| Fair Value Gap (FVG) | 1 pt |

- Minimum default confidence: **80%** (configurable via Admin Panel)
- Multi-timeframe: **15m · 1H · 4H** — best timeframe wins

---

## Signal Format

```
📊 Pair: EURUSD
📈 Signal: BUY
⏱ Timeframe: 1h

🎯 Entry:    1.12500
🛑 Stop Loss: 1.12200

✅ TP1: 1.12800
✅ TP2: 1.13100
✅ TP3: 1.13500

⚖️ Risk/Reward: 1:1.5
🔥 Accuracy Score: 89%

⚠️ This signal is generated automatically from market analysis
   and is not financial advice. Trading decisions remain the
   user's responsibility.
```

---

## Signal Tracker

After a signal is generated, the bot checks every 10 minutes:

- **TP1 Hit** → VIP users receive a 🎯 TP1 HIT notification
- **SL Hit** → VIP users receive a 🛑 STOP LOSS HIT notification
- Signals expire after 24 hours automatically

---

## User Interface

### Normal Users — 4 keyboard buttons

```
[ 📊 Select Pair ]  [ 📈 Get Signal ]
[ 💳 Subscription ] [ 💰 Payment    ]
```

### Admin — 5 keyboard buttons (admin sees extra row)

```
[ 📊 Select Pair ]  [ 📈 Get Signal ]
[ 💳 Subscription ] [ 💰 Payment    ]
[       ⚙️ Admin Panel              ]
```

> The Admin Panel button is **invisible** to normal users.
> The `/admin` command no longer exists.

---

## Admin Panel Features

| Section | What you can do |
|---------|-----------------|
| 📊 Statistics | Total users, VIP count, active today, recent signals |
| 📢 Broadcast | Message to all users OR VIP only |
| 👥 Manage Users | Grant/revoke VIP, ban/unban by Telegram ID |
| 💳 Payment Methods | Add · Edit · Delete payment methods |
| ⏳ Pending Payments | Approve ✅ or Reject ❌ with one tap |
| 📡 Recent Signals | Last 15 signals with status (active/tp1_hit/sl_hit) |
| ⚙️ Settings | Confidence threshold, enabled pairs, broadcast toggle, plan info |

### User Management Syntax (send as text after tapping Manage Users)
```
123456789 vip      → Grant VIP
123456789 devip    → Remove VIP
123456789 ban      → Ban user
123456789 unban    → Unban user
```

### Payment Method Syntax
```
Add:    NAME | DETAILS
Edit:   ID | NEW_NAME | NEW_DETAILS
Delete: ID
```

---

## Quick Start

### 1 — Extract & install

```bash
tar -xzf forex-smc-bot.tar.gz
cd forex-smc-bot
pip install -r requirements.txt
```

### 2 — Configure

```bash
cp .env.example .env
# Fill in BOT_TOKEN, TWELVE_API_KEY, ADMIN_ID
```

### 3 — Run

```bash
python bot.py
```

---

## Railway Deployment

1. Push folder to GitHub
2. Railway → **New Project → Deploy from GitHub**
3. Set environment variables in Railway dashboard:

| Variable | Value |
|----------|-------|
| `BOT_TOKEN` | BotFather token |
| `TWELVE_API_KEY` | twelvedata.com API key |
| `ADMIN_ID` | Your Telegram numeric user ID |

Railway reads `railway.json` automatically and starts the bot as a worker.

---

## Assets

Place real images in `assets/` to replace the generated placeholders:

| File | Used for |
|------|----------|
| `assets/logo.png` | Bot identity |
| `assets/welcome_banner.png` | Sent with /start welcome message |
| `assets/premium_banner.png` | Shown when a VIP-only signal is teased |
| `assets/signal_banner.png` | Sent alongside each full signal |

Recommended size: **600 × 200 px** for banners, **200 × 200 px** for logo.

---

## Project Structure

```
forex-smc-bot/
├── bot.py              ← Main entry point
├── config.py           ← Env vars + constants
├── database.py         ← SQLite ORM (all tables)
├── signals.py          ← Multi-TF signal engine
├── admin.py            ← Admin utilities
├── payments.py         ← Payment processing
├── subscriptions.py    ← Subscription lifecycle
├── broadcast.py        ← Message broadcasting
├── scheduler.py        ← Market scan + signal tracker + expiry
│
├── handlers/
│   ├── start.py        ← /start, keyboard setup
│   ├── pairs.py        ← Pair selection + market status
│   ├── signals.py      ← Signal display + VIP gate
│   ├── payments.py     ← Payment + subscription flow
│   └── admin.py        ← Full admin panel UI
│
├── smc/
│   ├── bos.py          ← Break of Structure
│   ├── choch.py        ← Change of Character
│   ├── liquidity.py    ← Liquidity Sweep
│   ├── orderblocks.py  ← Order Blocks
│   ├── fvg.py          ← Fair Value Gap
│   └── trend.py        ← EMA trend confirmation ← NEW
│
├── utils/
│   ├── api.py          ← Twelve Data client
│   ├── logger.py       ← Rotating file logger
│   └── helpers.py      ← Format + market-hours utils
│
├── assets/             ← Banner images ← NEW
│   ├── logo.png
│   ├── welcome_banner.png
│   ├── premium_banner.png
│   └── signal_banner.png
│
├── requirements.txt
├── Procfile
├── railway.json
├── runtime.txt
└── .env.example
```

---

## Security

- All secrets via environment variables only
- Rate limiting: 5-second cooldown per user
- Admin restricted to `ADMIN_ID` only (no `/admin` command)
- Payments require manual admin approval before VIP activation
- Rotating logs (5 MB cap, 3 backups)

---

## License

MIT — use freely, modify as needed.
