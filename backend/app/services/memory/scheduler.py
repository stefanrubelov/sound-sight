"""APScheduler setup for periodic background jobs.

Jobs:
  - Nightly baseline update (02:00 UTC) — recomputes per-class stats from 30 days of events
  - Hourly session purge — removes expired short-term session memories
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _nightly_baseline_job() -> None:
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.memory.baseline import run_baseline_update

        async with AsyncSessionLocal() as db:
            n = await run_baseline_update(db)
        log.info("Nightly baseline update complete: %d class(es) updated", n)
    except Exception as exc:
        log.error("Nightly baseline job failed: %s", exc)


async def _hourly_session_purge() -> None:
    try:
        from app.services.memory.session import purge_expired

        purge_expired()
    except Exception as exc:
        log.warning("Session purge job failed: %s", exc)


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
        _scheduler.add_job(
            _nightly_baseline_job,
            trigger="cron",
            hour=2,
            minute=0,
            id="nightly_baseline",
            replace_existing=True,
        )
        _scheduler.add_job(
            _hourly_session_purge,
            trigger="interval",
            hours=1,
            id="session_purge",
            replace_existing=True,
        )
    return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        log.info("APScheduler started (nightly baseline @ 02:00 UTC, hourly session purge)")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("APScheduler stopped")
