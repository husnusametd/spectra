"""CoinAPI tabanlı OHLCV veri çekici.

Basit kullanım örneği
---------------------
```python
from spectra.coinapi_fetcher import fetch_ohlcv
bars = await fetch_ohlcv("BTC", period="4H", limit=200)
print(bars[:3])
```
Dönen liste elemanları:
```
{
    "time_close": "2025-06-19T12:00:00.0000000Z",
    "open": 30123.1,
    "high": 30500.0,
    "low": 30000.5,
    "close": 30200.3,
    "volume": 1234.56
}
```
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Dict

import httpx
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("COINAPI_KEY")
if not API_KEY:
    logging.warning("COINAPI_KEY environment variable missing – requests will fail.")

BASE_URL = "https://rest.coinapi.io/v1/ohlcv/{symbol_id}/history"

# Basit dönem haritası – CoinAPI "period_id" formatı
_PERIOD_MAP = {
    "1D": "1DAY",
    "4H": "4HRS",
    "1H": "1HRS",
    "15m": "15MIN",
}

# Varsayılan borsa → BINANCE_SPOT
_EXCHANGE_PREFIX = "BINANCE_SPOT"

async def _fetch(client: httpx.AsyncClient, symbol: str, period: str, limit: int) -> List[Dict]:
    period_id = _PERIOD_MAP.get(period, period)
    symbol_id = f"{_EXCHANGE_PREFIX}_{symbol.upper()}_USDT"
    url = BASE_URL.format(symbol_id=symbol_id)

    params = {
        "period_id": period_id,
        "limit": limit,
    }
    headers = {"X-CoinAPI-Key": API_KEY}
    r = await client.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()

    # Normalize field names (lower snake_case)
    out = []
    for bar in data:
        out.append({
            "time_close": bar["time_close"],
            "open": bar["price_open"],
            "high": bar["price_high"],
            "low": bar["price_low"],
            "close": bar["price_close"],
            "volume": bar["volume_traded"],
        })
    return out


async def fetch_ohlcv(symbol: str, period: str = "4H", limit: int = 200) -> List[Dict]:
    """Tek sembol, tek dönem OHLCV getirir (liste-dict)."""
    async with httpx.AsyncClient(http2=True) as client:
        return await _fetch(client, symbol, period, limit)


async def fetch_multi(symbols: List[str], period: str = "4H", limit: int = 200) -> Dict[str, List[Dict]]:
    """Birden çok sembol için paralel OHLCV çeker."""
    async with httpx.AsyncClient(http2=True, limits=httpx.Limits(max_connections=10)) as client:
        tasks = [asyncio.create_task(_fetch(client, s, period, limit)) for s in symbols]
        bars_list = await asyncio.gather(*tasks, return_exceptions=True)

    result: Dict[str, List[Dict]] = {}
    for sym, bars in zip(symbols, bars_list):
        if isinstance(bars, Exception):
            logging.error("CoinAPI fetch failed for %s: %s", sym, bars)
        else:
            result[sym] = bars
    return result
