import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
TWELVE_API_KEY = os.environ["TWELVE_API_KEY"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

DATABASE_PATH = os.getenv("DATABASE_PATH", "database.db")

FOREX_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "GBPJPY"]
CRYPTO_PAIRS = ["XAUUSD", "BTCUSD"]
SUPPORTED_PAIRS = FOREX_PAIRS + CRYPTO_PAIRS

TIMEFRAMES = ["15min", "1h", "4h"]

SUBSCRIPTION_PLANS = {
    "1month":   {"name": "1 Month",   "days": 30},
    "3month":   {"name": "3 Months",  "days": 90},
    "lifetime": {"name": "Lifetime",  "days": 36500},
}

SIGNAL_SCAN_INTERVAL = 15 * 60
SIGNAL_TRACKER_INTERVAL = 10 * 60

DEFAULT_MIN_CONFIDENCE = 80

RATE_LIMIT_SECONDS = 5

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE  = os.getenv("LOG_FILE",  "bot.log")

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
