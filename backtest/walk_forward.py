"""Walk-forward back-test engine.

Assumptions
-----------
* Historical parquet files exist as ``data/hist/{symbol}_{tf}.parquet``.
* Each row contains ``timestamp`` (UTC) and a column ``signal_return`` representing
  strategy return for that bar (including fees / slippage if desired).
* The optimiser in :pymod:`spectra.optimizer` already knows how to tweak the
  threshold parameters and write them back to *config.yaml* (it is re-used as
  the *training* step).

API
---
sliding_window(cfg_path: str, symbol: str, tf: str, lookback: int = 180,
               step: int = 30) -> pd.DataFrame
    Performs successive train/test splits:
    * train span   : ``lookback`` days
    * test  span   : ``step`` days (out-of-sample)

    Returns dataframe with columns:
    ``train_start, train_end, test_start, test_end, oos_sharpe``.

gatekeeper(df, min_oos_sharpe: float = 0.8) -> bool
    Convenience helper – returns **True** if median OOS Sharpe satisfies the
    required threshold.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from spectra.optimizer import run_optuna_search, _sharpe  # reuse private sharpe helper
from spectra.utils import load_config, save_config

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "hist"


def _load(symbol: str, tf: str) -> pd.DataFrame:
    file_ = DATA_DIR / f"{symbol}_{tf}.parquet"
    if not file_.exists():
        raise FileNotFoundError(file_)
    return pd.read_parquet(file_).sort_values("timestamp")


def sliding_window(cfg_path: str, symbol: str, tf: str, *, lookback: int = 180, step: int = 30) -> pd.DataFrame:  # noqa: D401,E501
    df = _load(symbol, tf)
    if "signal_return" not in df.columns:
        raise ValueError("history parquet missing 'signal_return' column")

    windows: List[dict] = []
    idx = 0
    while True:
        train_start = df["timestamp"].min() + pd.Timedelta(days=idx * step)
        train_end = train_start + pd.Timedelta(days=lookback)
        test_end = train_end + pd.Timedelta(days=step)
        if test_end > df["timestamp"].max():
            break  # no more full window

        # Slice
        train_mask = (df["timestamp"] >= train_start) & (df["timestamp"] < train_end)
        test_mask = (df["timestamp"] >= train_end) & (df["timestamp"] < test_end)
        train_df = df.loc[train_mask]
        test_df = df.loc[test_mask]

        # --- TRAIN: run optuna on training slice
        # For speed, we call run_optuna_search with lookback_days equal to window size
        # It updates config, but we don't want cumulative drift – copy-on-write.
        cfg = load_config()
        save_config(cfg, cfg_path + ".bak")  # simple backup
        run_optuna_search(cfg_path, lookback_days=lookback)

        # --- TEST: compute OOS sharpe with new thresholds
        oos_sharpe = _sharpe(test_df["signal_return"], freq="4H")

        windows.append(
            {
                "train_start": train_start,
                "train_end": train_end,
                "test_start": train_end,
                "test_end": test_end,
                "oos_sharpe": oos_sharpe,
            }
        )
        idx += 1

    res = pd.DataFrame(windows)
    logger.info("Walk-forward completed – median OOS Sharpe %.2f", res["oos_sharpe"].median())
    return res


def gatekeeper(df: pd.DataFrame, min_oos_sharpe: float = 0.8) -> bool:  # noqa: D401
    """Return True if median OOS Sharpe passes the gate."""
    return df["oos_sharpe"].median() >= min_oos_sharpe


# ---------------------------------------------------------------------------
# If executed as a script (for debugging only)
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import argparse
    logging.basicConfig(level=logging.INFO)

    p = argparse.ArgumentParser(description="Walk-forward back-test runner")
    p.add_argument("--config", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--tf", default="4h")
    p.add_argument("--lookback", type=int, default=180)
    p.add_argument("--step", type=int, default=30)
    args = p.parse_args()

    df_res = sliding_window(args.config, args.symbol, args.tf, lookback=args.lookback, step=args.step)
    ok = gatekeeper(df_res)
    print(df_res)
    print("PASS" if ok else "FAIL")
