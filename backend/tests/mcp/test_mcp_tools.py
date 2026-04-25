"""Unit tests for each MCP tool — called directly against the test DB."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.db.models import Baseline, Device, Event, Rule, UserProfile
from app.mcp.server import (
    get_active_rules,
    get_device_status,
    get_sound_class_info,
    get_user_baseline,
    get_user_profile,
    mcp,
    query_events,
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _add(db_session, obj):
    db_session.add(obj)
    await db_session.commit()
    await db_session.refresh(obj)
    return obj


# ── Tool registration ─────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_mcp_registers_six_tools():
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "query_events",
        "get_device_status",
        "get_user_profile",
        "get_active_rules",
        "get_sound_class_info",
        "get_user_baseline",
    }


# ── query_events ──────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_query_events_empty(db_session, patched_db):
    result = await query_events()
    assert result == []


@pytest.mark.anyio
async def test_query_events_returns_event(db_session, patched_db):
    event = Event(
        device_id=0,
        class_name="doorbell",
        confidence=0.9,
        duration=1.5,
        timestamp=_now(),
    )
    await _add(db_session, event)

    result = await query_events()
    assert len(result) == 1
    assert result[0]["class_name"] == "doorbell"
    assert result[0]["confidence"] == pytest.approx(0.9)


@pytest.mark.anyio
async def test_query_events_filter_class(db_session, patched_db):
    for cls in ("doorbell", "fire_alarm", "doorbell"):
        await _add(
            db_session,
            Event(device_id=0, class_name=cls, confidence=0.8, duration=1.0, timestamp=_now()),
        )

    result = await query_events(class_name="doorbell")
    assert len(result) == 2
    assert all(e["class_name"] == "doorbell" for e in result)


@pytest.mark.anyio
async def test_query_events_limit(db_session, patched_db):
    for _ in range(5):
        await _add(
            db_session,
            Event(
                device_id=0, class_name="timer_beep", confidence=0.7, duration=0.5, timestamp=_now()
            ),
        )

    result = await query_events(limit=3)
    assert len(result) == 3


# ── get_device_status ─────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_get_device_status_not_found(db_session, patched_db):
    result = await get_device_status(device_id=999)
    assert "error" in result


@pytest.mark.anyio
async def test_get_device_status_found(db_session, patched_db):
    device = await _add(db_session, Device(name="hall sensor", room="hallway"))
    result = await get_device_status(device_id=device.id)
    assert result["name"] == "hall sensor"
    assert result["room"] == "hallway"
    assert result["online"] is False  # last_seen is None


# ── get_user_profile ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_get_user_profile_empty(db_session, patched_db):
    result = await get_user_profile()
    assert result["enabled_classes"] == []
    assert result["quiet_hours"] is None


@pytest.mark.anyio
async def test_get_user_profile_with_data(db_session, patched_db):
    profile = UserProfile(
        home_description="Small flat, living alone.",
        enabled_classes=json.dumps(["fire_alarm", "doorbell"]),
        quiet_hours=json.dumps({"start": "22:00", "end": "07:00"}),
    )
    await _add(db_session, profile)

    result = await get_user_profile()
    assert result["home_description"] == "Small flat, living alone."
    assert "fire_alarm" in result["enabled_classes"]
    assert result["quiet_hours"]["start"] == "22:00"


# ── get_active_rules ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_get_active_rules_empty(db_session, patched_db):
    result = await get_active_rules()
    assert result == []


@pytest.mark.anyio
async def test_get_active_rules_returns_rules(db_session, patched_db):
    rule = Rule(trigger="fire_alarm", priority="critical", alert_type="both")
    await _add(db_session, rule)

    result = await get_active_rules()
    assert len(result) == 1
    assert result[0]["trigger"] == "fire_alarm"
    assert result[0]["priority"] == "critical"


# ── get_sound_class_info ──────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_get_sound_class_info_known():
    result = await get_sound_class_info("fire_alarm")
    assert result["class_name"] == "fire_alarm"
    assert "Fire Alarm" in result["content"]
    assert "Safety Implications" in result["content"]


@pytest.mark.anyio
async def test_get_sound_class_info_all_classes():
    classes = [
        "fire_alarm",
        "doorbell",
        "glass_breaking",
        "baby_crying",
        "dog_barking",
        "timer_beep",
        "water_running",
    ]
    for cls in classes:
        result = await get_sound_class_info(cls)
        assert "error" not in result, f"Missing KB file for {cls}"
        assert result["class_name"] == cls


@pytest.mark.anyio
async def test_get_sound_class_info_unknown():
    result = await get_sound_class_info("chainsaw")
    assert "error" in result


# ── get_user_baseline ─────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_get_user_baseline_not_found(db_session, patched_db):
    result = await get_user_baseline("fire_alarm")
    assert result["available"] is False
    assert result["stats"] == {}


@pytest.mark.anyio
async def test_get_user_baseline_found(db_session, patched_db):
    baseline = Baseline(
        class_name="doorbell",
        stats_json=json.dumps(
            {"mean_duration": 1.5, "std_duration": 0.3, "mean_count_per_day": 3.0}
        ),
    )
    await _add(db_session, baseline)

    result = await get_user_baseline("doorbell", window_days=14)
    assert result["available"] is True
    assert result["stats"]["mean_duration"] == pytest.approx(1.5)
    assert result["window_days"] == 14
