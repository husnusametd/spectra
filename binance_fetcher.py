"""Binance Futures API veri çekici (REST).
Funding rate (public) ve open interest (imzalı) uç noktaları örnek olarak.
"""
from __future__ import annotations

import os
import time
import hmac
import hashlib
from typing import Any, Dict

import httpx

BASE_URL = "https://fapi.binance.com"

API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")


async def _signed_get(path: str, params: Dict[str, Any] | None = None) -> Dict:
    """İmza (HMAC SHA256) gerektiren GET isteği."""
    if not API_KEY or not API_SECRET:
        raise RuntimeError("BINANCE_API_KEY / BINANCE_API_SECRET env değişkenlerini ayarlayın")

    if params is None:
        params = {}
    params["timestamp"] = int(time.time() * 1000)
    query = "&".join(f"{k}={v}" for k, v in params.items())
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    headers = {"X-MBX-APIKEY": API_KEY}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}{path}?{query}&signature={signature}", headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()


async def funding_rate(symbol: str = "BTCUSDT") -> Dict:
    """Son funding oranını (public endpoint) döndürür."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/fapi/v1/fundingRate", params={"symbol": symbol, "limit": 1}, timeout=10
        )
        resp.raise_for_status()
        return resp.json()[0]


async def fetch_klines(symbol: str, interval: str = "4h", limit: int = 300):
    """Public endpoint - klines (candles) for futures market."""
    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/fapi/v1/klines", params=params, timeout=10)
        resp.raise_for_status()
        arr = resp.json()
        # Map to dict list matching CoinAPI keys
        return [
            {
                "time_close": k[6] / 1000,
                "open": k[1],
                "high": k[2],
                "low": k[3],
                "close": k[4],
                "volume": k[5],
            }
            for k in arr
        ]

async def fetch_depth(symbol: str, limit: int = 1000) -> dict:
    """Order-book depth snapshot. Returns bids/asks arrays."""
    params = {"symbol": symbol.upper(), "limit": limit}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/fapi/v1/depth", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

async def orderbook_imbalance_usd(symbol: str, depth_limit: int = 1000, levels: int = 50) -> float:
    """Compute absolute USD imbalance between bid and ask sides for first N levels."""
    depth = await fetch_depth(symbol, depth_limit)
    bids = depth.get("bids", [])[:levels]
    asks = depth.get("asks", [])[:levels]
    bid_usd = sum(float(p) * float(q) for p, q in bids)
    ask_usd = sum(float(p) * float(q) for p, q in asks)
    return abs(bid_usd - ask_usd)


async def open_interest(symbol: str = "BTCUSDT") -> Dict:
    """Açık faiz tarihi (imzalı)."""
    return await _signed_get("/futures/data/openInterestHist", {"symbol": symbol, "period": "5m", "limit": 1})
