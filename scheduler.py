"""Asyncio tabanlı zamanlayıcı: 00:05, 08:05, 12:35, 20:05 UTC."""
from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta, timezone
from typing import Awaitable, Callable, List
import logging

RUN_UTC_TIMES: List[time] = [
    time(0, 5),
    time(8, 5),
    time(12, 35),
    time(20, 5),
]


def _next_run_datetime(now: datetime) -> datetime:
    """Şu andan sonraki en yakın planlı zamanı döndürür."""
    today_runs = [
        datetime.combine(now.date(), t, tzinfo=timezone.utc) for t in RUN_UTC_TIMES
    ]
    future = [dt for dt in today_runs if dt > now]
    return (future[0] if future else today_runs[0] + timedelta(days=1)).astimezone(
        timezone.utc
    )


async def scheduler(job: Callable[[], Awaitable[None]]):
    """job coroutine'ini belirli zamanlarda tetikler."""
    while True:
        now = datetime.now(timezone.utc)
        next_dt = _next_run_datetime(now)
        sleep_seconds = (next_dt - now).total_seconds()
        logging.info("Next run at %s UTC (%.0f s)", next_dt.isoformat(), sleep_seconds)
        await asyncio.sleep(sleep_seconds)
        try:
            await job()
        except Exception:
            logging.exception("Scheduled job failed")
