"""Long-term memory: per-class sound baselines.

Queries the last BASELINE_WINDOW_DAYS of events, computes statistics per class,
persists them to the `Baseline` table, and embeds a text summary in ChromaDB so
agents can retrieve them semantically.

Stats stored per class:
    count_per_day       — average events per 24 hours
    mean_duration       — mean event duration (seconds)
    std_duration        — standard deviation of duration (seconds)
    mean_confidence     — mean classifier confidence
    night_ratio         — fraction of events between 22:00 and 06:00 UTC
    total_events        — raw event count in the window
"""

from __future__ import annotations

import json
import logging
import statistics
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Baseline, Event

log = logging.getLogger(__name__)

BASELINE_WINDOW_DAYS = 30


def _is_night(ts: datetime) -> bool:
    """True if timestamp falls between 22:00 and 06:00 UTC."""
    h = ts.hour if ts.tzinfo else ts.replace(tzinfo=timezone.utc).hour
    return h >= 22 or h < 6


def _compute_stats(events: list[Event]) -> dict:
    durations = [e.duration for e in events]
    confidences = [e.confidence for e in events]
    night_count = sum(1 for e in events if _is_night(e.timestamp))
    total = len(events)
    return {
        "total_events": total,
        "count_per_day": round(total / BASELINE_WINDOW_DAYS, 3),
        "mean_duration": round(statistics.mean(durations), 3) if durations else 0.0,
        "std_duration": round(statistics.stdev(durations), 3) if len(durations) > 1 else 0.0,
        "mean_confidence": round(statistics.mean(confidences), 3) if confidences else 0.0,
        "night_ratio": round(night_count / total, 3) if total else 0.0,
    }


async def compute_baselines(db: AsyncSession) -> dict[str, dict]:
    """Return {class_name: stats_dict} for the last BASELINE_WINDOW_DAYS."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=BASELINE_WINDOW_DAYS)
    result = await db.execute(
        select(Event).where(Event.timestamp >= cutoff, Event.class_name != "unknown")
    )
    events: list[Event] = list(result.scalars().all())

    by_class: dict[str, list[Event]] = {}
    for e in events:
        by_class.setdefault(e.class_name, []).append(e)

    return {cls: _compute_stats(evts) for cls, evts in by_class.items()}


async def save_baselines(db: AsyncSession, baselines: dict[str, dict]) -> None:
    """Upsert computed baselines into the Baseline table."""
    for class_name, stats in baselines.items():
        result = await db.execute(select(Baseline).where(Baseline.class_name == class_name))
        baseline = result.scalar_one_or_none()
        if baseline is None:
            baseline = Baseline(class_name=class_name, stats_json="{}")
            db.add(baseline)
        baseline.stats_json = json.dumps(stats)
        baseline.updated_at = datetime.now(timezone.utc)

    await db.commit()
    log.info("Saved baselines for %d class(es)", len(baselines))


def embed_baselines(baselines: dict[str, dict]) -> None:
    """Embed baseline summaries into ChromaDB for agent semantic retrieval."""
    try:
        from app.services.rag.chroma_client import get_collection, upsert_texts

        texts, metadatas, ids = [], [], []
        for class_name, stats in baselines.items():
            label = class_name.replace("_", " ")
            text = (
                f"{label} baseline: {stats['count_per_day']:.1f} events/day on average, "
                f"typical duration {stats['mean_duration']:.1f}s "
                f"(±{stats['std_duration']:.1f}s), "
                f"{stats['night_ratio']:.0%} at night."
            )
            texts.append(text)
            metadatas.append({**stats, "class_name": class_name, "type": "baseline"})
            ids.append(f"baseline-{class_name}")

        if texts:
            col = get_collection("baselines")
            upsert_texts(col, texts=texts, metadatas=metadatas, ids=ids)
            log.debug("Embedded %d baseline(s) into ChromaDB", len(texts))
    except Exception as exc:
        log.warning("Baseline ChromaDB embedding failed: %s", exc)


async def run_baseline_update(db: AsyncSession) -> int:
    """Compute, save, and embed all baselines. Returns the number of classes updated."""
    baselines = await compute_baselines(db)
    if not baselines:
        log.info("No events found in window — skipping baseline update")
        return 0
    await save_baselines(db, baselines)
    embed_baselines(baselines)
    return len(baselines)
