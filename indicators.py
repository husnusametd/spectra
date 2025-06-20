"""Basit teknik indikatör hesaplamaları.
Gerçek veriler pandas DataFrame (datetime index, OHLCV kolonları) olarak verilmelidir.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    roll_up = pd.Series(gain, index=series.index).rolling(period).mean()
    roll_down = pd.Series(loss, index=series.index).rolling(period).mean()
    rs = roll_up / roll_down
    return 100 - (100 / (1 + rs))


def bollinger_width(series: pd.Series, period: int = 20, num_std: float = 2.0) -> pd.Series:
    ma = series.rolling(period).mean()
    std = series.rolling(period).std(ddof=0)
    upper = ma + num_std * std
    lower = ma - num_std * std
    width = (upper - lower) / ma * 100  # yüzde
    return width


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def vol_zscore(series: pd.Series, window: int = 20) -> pd.Series:
    vol = series.pct_change().abs()
    mean = vol.rolling(window).mean()
    std = vol.rolling(window).std(ddof=0)
    return (vol - mean) / std
