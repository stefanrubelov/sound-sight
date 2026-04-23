"""
Seed the database with a default UserProfile + sample Device for dev.
Run from repo root: python scripts/seed_db.py
Implemented in Phase 1 once models + DB session are wired up.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


async def main() -> None:
    from app.db.session import AsyncSessionLocal
    from app.db.models import Device, UserProfile

    async with AsyncSessionLocal() as session:
        profile = UserProfile(
            home_description="Single occupant, apartment. Care about fire alarm, doorbell, glass breaking.",
            enabled_classes=["fire_alarm", "doorbell", "glass_breaking", "baby_crying"],
            quiet_hours='{"start": "22:00", "end": "07:00"}',
            notes="Demo seed profile",
        )
        session.add(profile)

        device = Device(
            name="Living Room Sensor",
            room="living_room",
        )
        session.add(device)

        await session.commit()
        print("Seeded: 1 UserProfile, 1 Device")


if __name__ == "__main__":
    asyncio.run(main())
