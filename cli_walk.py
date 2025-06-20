"""CLI entry-point for walk-forward back-test.

Usage
-----
python cli_walk.py --config spectra/config.yaml --symbol BTCUSDT --tf 4h \
                   --lookback 180 --step 30
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from spectra.backtest.walk_forward import sliding_window, gatekeeper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:  # noqa: D401
    p = argparse.ArgumentParser(description="Walk-Forward Back-Test Runner")
    p.add_argument("--config", required=True, help="Path to config.yaml")
    p.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    p.add_argument("--tf", default="4h", help="Time-frame identifier, e.g. 4h")
    p.add_argument("--lookback", type=int, default=180, help="Training window length in days")
    p.add_argument("--step", type=int, default=30, help="Out-of-sample window length in days")
    args = p.parse_args()

    cfg_path = Path(args.config)
    df_res = sliding_window(str(cfg_path), args.symbol, args.tf, lookback=args.lookback, step=args.step)
    print(df_res)

    ok = gatekeeper(df_res)
    print("\nGatekeeper:", "PASS ✅" if ok else "FAIL ❌")


if __name__ == "__main__":
    main()
