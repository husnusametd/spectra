"""Ana giriş noktası – zamanlayıcıyı başlatır.

Yalnızca `python main.py` komutu ile sürekli çalışan mod.
Cron ile kullanılacaksa scheduler içindeki döngü yerine doğrudan run_once
fonksiyonu çağrılabilir.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List

from spectra.data_fetcher import fetch_top_500
from spectra.signal_engine import evaluate_signals
from spectra.mailer import send_email
from spectra.scheduler import scheduler
from spectra.utils import setup_logging, load_config, round_to_tick


async def run_once(debug_print: bool = False) -> list[dict]:
    cfg = load_config()
    setup_logging(cfg["logging"]["path"], cfg["logging"]["retention_days"])

    assets = await fetch_top_500()

    rows: List[dict] = []
    for asset in assets:
        signals = evaluate_signals(asset)
        true_sigs = [s for s in signals if s["true"]]
        if not true_sigs:
            continue
        sig = true_sigs[0]

        # Dummy metrikler – atr yerine 24h pct değişimi kullanıldı.
        price = asset["current_price"]
        atr_proxy = abs(asset.get("price_change_percentage_24h") or 0) / 100 * price
        sl = round_to_tick(price - 0.8 * atr_proxy, asset["symbol"])
        tp1 = round_to_tick(price + 1.6 * atr_proxy, asset["symbol"])
        tp2 = round_to_tick(price + 3 * atr_proxy, asset["symbol"])

        rows.append(
            dict(
                rank=asset["market_cap_rank"],
                ticker=asset["symbol"].upper(),
                signal=sig["name"],
                conviction=sig["conviction"],
                entry=price,
                sl=sl,
                tp1=tp1,
                tp2=tp2,
                ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )
        )

    if debug_print:
        for r in rows:
            print(r)
    else:
        await send_email(rows)


def main():
    asyncio.run(scheduler(run_once))


if __name__ == "__main__":
    main()
