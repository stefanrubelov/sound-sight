"""Seed the database for development and demo.

Seeds:
  - 1 UserProfile (default preferences)
  - 1 Device (Living Room Sensor)
  - ~14 days of plausible sound events (realistic class distribution + timing)
  - Baselines computed from that event history

Run from repo root:
    python scripts/seed_db.py [--days 14] [--clear]

Options:
  --days N   How many days of events to generate (default: 14)
  --clear    Drop and re-create all rows before seeding (idempotent re-run)
"""

import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# ── Event distribution ─────────────────────────────────────────────────────────
# (class_name, avg_per_day, typical_duration_s, std_duration_s, day_hours_only)
EVENT_PROFILE = [
    ("doorbell", 2.5, 0.8, 0.2, True),  # daytime only
    ("dog_barking", 3.0, 3.5, 1.5, False),
    ("timer_beep", 4.0, 0.5, 0.1, True),
    ("water_running", 5.0, 8.0, 3.0, False),
    ("baby_crying", 1.5, 45.0, 20.0, False),
    ("fire_alarm", 0.15, 4.0, 1.0, False),  # rare
    ("glass_breaking", 0.05, 0.6, 0.2, False),  # very rare
]

# Confidence range per class (min, max)
CONFIDENCE_RANGE: dict[str, tuple[float, float]] = {
    "doorbell": (0.80, 0.98),
    "dog_barking": (0.70, 0.95),
    "timer_beep": (0.85, 0.99),
    "water_running": (0.75, 0.95),
    "baby_crying": (0.65, 0.92),
    "fire_alarm": (0.88, 0.99),
    "glass_breaking": (0.82, 0.99),
}

# LLM summaries for demo realism (one per class, rotated)
SUMMARIES: dict[str, list[str]] = {
    "doorbell": [
        "Someone rang the doorbell in the living room.",
        "A doorbell chime was detected — someone may be at the door.",
        "The front doorbell rang briefly.",
    ],
    "dog_barking": [
        "The dog barked for a few seconds — possibly reacting to outdoor noise.",
        "Brief dog barking detected in the living room.",
        "The dog barked, likely triggered by activity outside.",
    ],
    "timer_beep": [
        "A timer beeped — a cooking or appliance timer may have finished.",
        "Short timer alert detected.",
        "Timer beep noted; check your kitchen appliances.",
    ],
    "water_running": [
        "Water running detected — sink, shower, or dishwasher in use.",
        "Running water sound noted for an extended period.",
        "Water flow detected, consistent with normal household use.",
    ],
    "baby_crying": [
        "Baby crying detected for an extended period — attention may be needed.",
        "The baby cried; the sound lasted longer than usual.",
        "Baby crying noted — consider checking in.",
    ],
    "fire_alarm": [
        "Fire alarm sounded. Please verify this is not a real emergency.",
        "The smoke detector activated briefly. Check for smoke or burning smells.",
    ],
    "glass_breaking": [
        "A glass-breaking sound was detected. Please check your surroundings.",
        "Breaking glass detected — investigate the area for safety.",
    ],
}


def _random_time_in_day(date: datetime, day_only: bool) -> datetime:
    """Return a random UTC datetime within the given date."""
    if day_only:
        hour = random.randint(7, 21)
    else:
        hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return date.replace(hour=hour, minute=minute, second=second, microsecond=0)


def _generate_events(device_id: int, days: int) -> list[dict]:
    """Generate a realistic list of event dicts spanning `days` days."""
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    events = []

    for day_offset in range(days):
        day = now - timedelta(days=days - day_offset)
        for class_name, avg_per_day, mean_dur, std_dur, day_only in EVENT_PROFILE:
            count = max(0, round(random.gauss(avg_per_day, avg_per_day * 0.4)))
            for _ in range(count):
                duration = max(0.1, random.gauss(mean_dur, std_dur))
                confidence_lo, confidence_hi = CONFIDENCE_RANGE.get(class_name, (0.70, 0.95))
                confidence = random.uniform(confidence_lo, confidence_hi)
                ts = _random_time_in_day(day, day_only)
                summaries = SUMMARIES.get(class_name, [])
                summary = random.choice(summaries) if summaries else None
                events.append(
                    {
                        "device_id": device_id,
                        "class_name": class_name,
                        "confidence": round(confidence, 3),
                        "duration": round(duration, 2),
                        "timestamp": ts,
                        "llm_summary": summary,
                    }
                )

    events.sort(key=lambda e: e["timestamp"])
    return events


def _compute_baselines(events: list[dict]) -> list[dict]:
    """Compute per-class duration + count stats from generated events."""
    from collections import defaultdict

    buckets: dict[str, list[float]] = defaultdict(list)
    day_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for e in events:
        class_name = e["class_name"]
        buckets[class_name].append(e["duration"])
        day_key = e["timestamp"].strftime("%Y-%m-%d")
        day_counts[class_name][day_key] += 1

    baselines = []
    for class_name, durations in buckets.items():
        n = len(durations)
        mean_dur = sum(durations) / n
        variance = sum((d - mean_dur) ** 2 for d in durations) / max(n - 1, 1)
        std_dur = variance**0.5

        counts = list(day_counts[class_name].values())
        mean_count = sum(counts) / len(counts)

        baselines.append(
            {
                "class_name": class_name,
                "stats_json": json.dumps(
                    {
                        "mean_duration": round(mean_dur, 3),
                        "std_duration": round(std_dur, 3),
                        "mean_count_per_day": round(mean_count, 2),
                        "sample_size": n,
                    }
                ),
            }
        )

    return baselines


async def main(days: int, clear: bool) -> None:
    from sqlalchemy import delete

    from app.db.models import Baseline, Base, Device, Event, UserProfile
    from app.db.session import AsyncSessionLocal, engine

    async with engine.begin() as conn:
        if clear:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        if clear:
            for model in (Baseline, Event, Device, UserProfile):
                await session.execute(delete(model))
            await session.commit()
            print("Cleared existing data.")

        # UserProfile
        profile = UserProfile(
            home_description=(
                "Single occupant, apartment in the city. "
                "Care most about fire alarms, doorbells, and glass breaking. "
                "Quiet hours are 22:00–07:00."
            ),
            enabled_classes=json.dumps(
                ["fire_alarm", "doorbell", "glass_breaking", "baby_crying", "dog_barking"]
            ),
            quiet_hours=json.dumps({"start": "22:00", "end": "07:00"}),
            notes="Demo profile — seeded for the exam presentation.",
        )
        session.add(profile)

        # Device
        device = Device(name="Living Room Sensor", room="living_room")
        session.add(device)
        await session.flush()  # get device.id

        # Events
        event_dicts = _generate_events(device.id, days)
        for e in event_dicts:
            session.add(Event(**e))

        await session.commit()
        print(f"Seeded: 1 UserProfile, 1 Device, {len(event_dicts)} Events over {days} days.")

        # Baselines
        baseline_dicts = _compute_baselines(event_dicts)
        for b in baseline_dicts:
            session.add(Baseline(**b))
        await session.commit()
        print(f"Seeded: {len(baseline_dicts)} Baselines.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the SoundSight demo database")
    parser.add_argument("--days", type=int, default=14, help="Days of history to generate")
    parser.add_argument("--clear", action="store_true", help="Clear existing data first")
    args = parser.parse_args()
    asyncio.run(main(args.days, args.clear))
