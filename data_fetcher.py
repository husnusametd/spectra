"""CoinGecko veri çekici – top-500 mcap kriptopara listesi."""
from __future__ import annotations

import asyncio
from typing import List, Dict, Any
import httpx
import pandas as pd
import logging

from .utils import load_config
from .coinapi_fetcher import fetch_ohlcv
from .binance_fetcher import fetch_klines, orderbook_imbalance_usd
from .indicators import ema, bollinger_width, vol_zscore

CFG = load_config()
CG_URL: str = CFG["coingecko"]["url"]
CG_PARAMS_BASE: Dict[str, str] = CFG["coingecko"]["params"]


async def _fetch_page(client: httpx.AsyncClient, page: int) -> List[Dict]:
    params = CG_PARAMS_BASE | {"page": page}
    r = await client.get(CG_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


async def _enrich_with_indicators(asset: Dict[str, Any]) -> Dict[str, Any]:
    """CoinAPI'den OHLCV çekip temel indikatörleri hesaplar."""
    symbol = asset["symbol"]
    try:
        bars = await fetch_ohlcv(symbol, period="4H", limit=120)
        if not bars:
            # Fallback Binance Futures klines
            bars = await fetch_klines(f"{symbol.upper()}USDT", interval="4h", limit=120)
        if not bars:
            return asset
        df = pd.DataFrame(bars)
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df.dropna(subset=["close"], inplace=True)
        if len(df) < 60:
            return asset
        df.set_index(pd.to_datetime(df["time_close"]), inplace=True)
        close = df["close"]
        asset.update({
            "Price_4H": float(close.iloc[-1]),
            "EMA21_4H": float(ema(close, 21).iloc[-1]),
            "EMA50_4H": float(ema(close, 50).iloc[-1]),
            "BB_Width_4H": float(bollinger_width(close).iloc[-1]),
        })
    except Exception as exc:
        logging.error("Indicator enrichment failed for %s: %s", symbol, exc)
    # 1H vol zscore
    try:
        bars1h = await fetch_ohlcv(symbol, period="1H", limit=200) or await fetch_klines(f"{symbol.upper()}USDT", interval="1h", limit=200)
        if bars1h:
            df1 = pd.DataFrame(bars1h)
            df1["close"] = pd.to_numeric(df1["close"], errors="coerce")
            df1.dropna(subset=["close"], inplace=True)
            close1 = df1["close"]
            asset["Vol_Z_1H"] = float(vol_zscore(close1).iloc[-1])
    except Exception as exc:
        logging.error("Vol zscore fetch failed for %s: %s", symbol, exc)
    # Orderbook imbalance
    try:
        asset["OB_Imbalance_USD"] = await orderbook_imbalance_usd(f"{symbol.upper()}USDT")
    except Exception as exc:
        logging.error("Orderbook imbalance fetch failed for %s: %s", symbol, exc)
    return asset


async def fetch_top_500() -> List[Dict]:
    """Per_page=250 * 2 sayfa ile 500 varlık getirir ve indikatörlerle zenginleştirir."""
    async with httpx.AsyncClient(http2=True, limits=httpx.Limits(max_connections=10)) as client:
        data_pages = await asyncio.gather(*[_fetch_page(client, p) for p in (1, 2)])
    assets = [item for page in data_pages for item in page]
    logging.info("Fetched %s assets from CoinGecko", len(assets))

    # Enrichment (sembol sayısı çok olduğundan ilk N için demo)
    top_assets = assets  # tüm 500 varlık
    enriched = await asyncio.gather(*[_enrich_with_indicators(a) for a in top_assets])
    return enriched
