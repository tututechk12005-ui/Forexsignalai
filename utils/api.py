import httpx
import logging
from typing import Optional
from config import TWELVE_API_KEY

logger = logging.getLogger(__name__)
BASE_URL = "https://api.twelvedata.com"


async def fetch_ohlcv(symbol: str, interval: str, outputsize: int = 100) -> Optional[list]:
    params = {
        "symbol":     symbol,
        "interval":   interval,
        "outputsize": outputsize,
        "apikey":     TWELVE_API_KEY,
        "format":     "JSON",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/time_series", params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "error":
                logger.error("Twelve Data error for %s %s: %s", symbol, interval, data.get("message"))
                return None
            candles = []
            for v in reversed(data.get("values", [])):
                candles.append({
                    "datetime": v["datetime"],
                    "open":   float(v["open"]),
                    "high":   float(v["high"]),
                    "low":    float(v["low"]),
                    "close":  float(v["close"]),
                    "volume": float(v.get("volume", 0)),
                })
            return candles
    except httpx.HTTPError as e:
        logger.error("HTTP error %s %s: %s", symbol, interval, e)
        return None
    except Exception as e:
        logger.exception("Unexpected OHLCV error: %s", e)
        return None


async def fetch_latest_price(symbol: str) -> Optional[float]:
    params = {"symbol": symbol, "apikey": TWELVE_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BASE_URL}/price", params=params)
            resp.raise_for_status()
            return float(resp.json()["price"])
    except Exception as e:
        logger.error("Price fetch error %s: %s", symbol, e)
        return None
