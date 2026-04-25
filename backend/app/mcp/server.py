"""FastMCP server — provides all SoundSight tools to LangChain agents and external MCP clients."""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from app.db.session import AsyncSessionLocal

log = logging.getLogger(__name__)

_KB_DIR = Path(__file__).parents[3] / "rag" / "corpus" / "sound_classes"

mcp = FastMCP("SoundSight", stateless_http=True)


# ── Tool 1: query_events ──────────────────────────────────────────────────────


@mcp.tool()
async def query_events(
    class_name: str | None = None,
    room: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Query sound detection events with optional filters.

    Args:
        class_name: Filter by sound class (e.g. fire_alarm, doorbell).
        room: Filter by device room name.
        from_ts: Start of time range (ISO 8601). Defaults to 24 hours ago.
        to_ts: End of time range (ISO 8601). Defaults to now.
        limit: Maximum number of events to return (default 20, max 100).
    """
    from sqlalchemy import select

    from app.db.models import Device, Event

    limit = min(int(limit), 100)
    ts_from = (
        datetime.fromisoformat(from_ts)
        if from_ts
        else datetime.now(timezone.utc) - timedelta(hours=24)
    )
    ts_to = datetime.fromisoformat(to_ts) if to_ts else datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        q = select(Event).where(Event.timestamp >= ts_from, Event.timestamp <= ts_to)
        if class_name:
            q = q.where(Event.class_name == class_name)
        if room:
            q = q.join(Device).where(Device.room == room)
        q = q.order_by(Event.timestamp.desc()).limit(limit)
        result = await db.execute(q)
        events = result.scalars().all()
        return [
            {
                "id": e.id,
                "class_name": e.class_name,
                "confidence": e.confidence,
                "duration": e.duration,
                "timestamp": e.timestamp.isoformat(),
                "device_id": e.device_id,
                "llm_summary": e.llm_summary,
            }
            for e in events
        ]


# ── Tool 2: get_device_status ─────────────────────────────────────────────────


@mcp.tool()
async def get_device_status(device_id: int) -> dict:
    """Get the current status of a registered SoundSight device.

    Args:
        device_id: The integer ID of the device.
    """
    from app.db.models import Device

    async with AsyncSessionLocal() as db:
        device = await db.get(Device, device_id)
        if device is None:
            return {"error": f"Device {device_id} not found"}
        online = (
            (datetime.now(timezone.utc) - device.last_seen).total_seconds() < 300
            if device.last_seen
            else False
        )
        return {
            "id": device.id,
            "name": device.name,
            "room": device.room,
            "registered_at": device.registered_at.isoformat(),
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "online": online,
        }


# ── Tool 3: get_user_profile ──────────────────────────────────────────────────


@mcp.tool()
async def get_user_profile() -> dict:
    """Get the current user profile including enabled sound classes and quiet hours."""
    from sqlalchemy import select

    from app.db.models import UserProfile

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserProfile).limit(1))
        profile = result.scalar_one_or_none()
        if profile is None:
            return {
                "home_description": None,
                "enabled_classes": [],
                "quiet_hours": None,
                "notes": None,
            }
        return {
            "id": profile.id,
            "home_description": profile.home_description,
            "enabled_classes": (
                json.loads(profile.enabled_classes) if profile.enabled_classes else []
            ),
            "quiet_hours": json.loads(profile.quiet_hours) if profile.quiet_hours else None,
            "notes": profile.notes,
        }


# ── Tool 4: get_active_rules ──────────────────────────────────────────────────


@mcp.tool()
async def get_active_rules() -> list[dict]:
    """Get all active alert rules configured by the user."""
    from sqlalchemy import select

    from app.db.models import Rule

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Rule).order_by(Rule.created_at.desc()))
        rules = result.scalars().all()
        return [
            {
                "id": r.id,
                "trigger": r.trigger,
                "priority": r.priority,
                "alert_type": r.alert_type,
                "time_start": r.time_start,
                "time_end": r.time_end,
                "source_text": r.source_text,
                "created_at": r.created_at.isoformat(),
            }
            for r in rules
        ]


# ── Tool 5: get_sound_class_info ──────────────────────────────────────────────


@mcp.tool()
async def get_sound_class_info(class_name: str) -> dict:
    """Get knowledge-base information about a sound class.

    Args:
        class_name: Name of the sound class (e.g. fire_alarm, doorbell).
    """
    kb_file = _KB_DIR / f"{class_name}.md"
    if not kb_file.exists():
        return {"error": f"No KB entry for '{class_name}'", "class_name": class_name}
    return {
        "class_name": class_name,
        "content": kb_file.read_text(encoding="utf-8"),
    }


# ── Tool 6: get_user_baseline ─────────────────────────────────────────────────


@mcp.tool()
async def get_user_baseline(class_name: str, window_days: int = 30) -> dict:
    """Get the user's historical baseline statistics for a sound class.

    Args:
        class_name: The sound class to retrieve baseline for.
        window_days: Number of days the baseline covers (informational).
    """
    from sqlalchemy import select

    from app.db.models import Baseline

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Baseline).where(Baseline.class_name == class_name))
        baseline = result.scalar_one_or_none()
        if baseline is None:
            return {"class_name": class_name, "available": False, "stats": {}}
        return {
            "class_name": class_name,
            "available": True,
            "window_days": window_days,
            "updated_at": baseline.updated_at.isoformat(),
            "stats": json.loads(baseline.stats_json) if baseline.stats_json else {},
        }
