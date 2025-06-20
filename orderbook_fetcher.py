"""Binance order-book snapshot ile likidite kümesi metrikleri.
Yaklaşım (basit):
1. `/fapi/v1/depth?limit=1000` ile bid/ask listesi alınır.
2. Her fiyat seviyesindeki nominal USD hacmi = price * qty
3. 0.5% fiyat aralığında (varsayılan) en büyük kümeyi bulur.
   Bu kümenin toplam usd hacmi `liq_cluster_usd`,
   mevcut fiyatla yüzdesel mesafesi `liq_proximity_pct`.
"""
from __future__ import annotations

import httpx
from typing import Tuple, Dict

BASE_URL = "https://fapi.binance.com"


async def _depth_snapshot(symbol: str, limit: int = 1000) -> Dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/fapi/v1/depth", params={"symbol": symbol, "limit": limit}, timeout=10)
        r.raise_for_status()
        return r.json()


async def liquidity_metrics(symbol: str = "BTCUSDT", cluster_pct: float = 0.5) -> Tuple[float, float]:
    """Döndürür: (liq_cluster_usd, proximity_pct)"""
    snap = await _depth_snapshot(symbol)
    bids = [(float(p), float(q)) for p, q in snap["bids"]]
    asks = [(float(p), float(q)) for p, q in snap["asks"]]
    if not bids or not asks:
        return 0.0, 0.0

    # mid price (basit): en iyi bid/ask ortalaması
    mid = (bids[0][0] + asks[0][0]) / 2

    bucket_high = mid * (1 + cluster_pct / 100)
    bucket_low = mid * (1 - cluster_pct / 100)

    # Tüm seviyelerden aralık içindekileri topla
    cluster_usd = 0.0
    nearest_price = None
    for price, qty in bids + asks:
        if bucket_low <= price <= bucket_high:
            usd = price * qty
            cluster_usd += usd
            if nearest_price is None or abs(price - mid) < abs(nearest_price - mid):
                nearest_price = price

    proximity_pct = abs(nearest_price - mid) / mid * 100 if nearest_price else 0.0
    return cluster_usd, proximity_pct
