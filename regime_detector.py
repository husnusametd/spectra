"""Market regime detection (trend / range / high-vol) using Hurst exponent & realised volatility."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _compute_hurst(series: pd.Series, max_lag: int = 100) -> float:
    """Estimate Hurst exponent using rescaled range (R/S) analysis."""
    lags = range(2, max_lag)
    tau = [np.std(series.diff(lag).dropna()) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0  # H = slope*2


def detect_regime(df: pd.DataFrame) -> str:
    """Detect market regime given 4H OHLCV DataFrame w/ 'close'."""
    if len(df) < 500:
        return "range"
    close = df["close"].astype(float)
    hurst = _compute_hurst(close.tail(500))
    vol_series = close.pct_change().rolling(30).std()
    vol = vol_series.iloc[-1]
    if vol_series.isna().all():
        return "range"
    q60 = vol_series.quantile(0.6)
    q80 = vol_series.quantile(0.8)

    if hurst > 0.55 and vol < q60:
        return "trend"
    elif vol > q80:
        return "high_vol"
    return "range"
