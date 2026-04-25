"""LangChain chains for SoundSight."""

import logging

from app.services.llm.chains.event_interpreter import interpret_event
from app.services.llm.chains.onboarding_profiler import SoundProfile, build_profile
from app.services.llm.chains.rule_parser import ParsedRule, parse_rule

log = logging.getLogger(__name__)

__all__ = [
    "summarise_event",
    "interpret_event",
    "parse_rule",
    "ParsedRule",
    "build_profile",
    "SoundProfile",
]


async def summarise_event(class_name: str, event_id: int) -> str:
    """Generate a short LLM summary for a sound event.

    Opens its own DB session so it is safe to call from a background task
    after the originating request session may have been closed.
    """
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.db.models import Device, Event, UserProfile
    from app.db.session import AsyncSessionLocal

    device_name = "sensor"
    room = "unknown room"
    confidence = 0.0
    duration = 1.0
    user_notes = ""
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        async with AsyncSessionLocal() as db:
            event = await db.get(Event, event_id)
            if event:
                duration = event.duration
                confidence = event.confidence
                timestamp = event.timestamp.isoformat()
                if event.device_id:
                    device = await db.get(Device, event.device_id)
                    if device:
                        device_name = device.name
                        room = device.room

            result = await db.execute(select(UserProfile).limit(1))
            profile = result.scalar_one_or_none()
            if profile and profile.notes:
                user_notes = profile.notes
    except Exception as exc:
        log.warning("summarise_event: DB lookup failed: %s", exc)

    return await interpret_event(
        class_name=class_name,
        confidence=confidence,
        duration=duration,
        device_name=device_name,
        room=room,
        timestamp=timestamp,
        user_notes=user_notes,
    )
