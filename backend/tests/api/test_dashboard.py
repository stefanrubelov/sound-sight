"""Tests for GET /api/dashboard/summary."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.db.models import Device, Event, Rule


async def _seed_device(db_session) -> Device:
    device = Device(name="Sensor", room="kitchen", registered_at=datetime.now(timezone.utc))
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


# ---------------------------------------------------------------------------
# GET /api/dashboard/summary — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dashboard_summary_empty_db(client):
    resp = await client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["events_today"] == 0
    assert body["events_this_week"] == 0
    assert body["most_active_class"] is None
    assert body["active_device_count"] == 0
    assert body["active_rule_count"] == 0


@pytest.mark.anyio
async def test_dashboard_summary_counts_events(client, db_session):
    device = await _seed_device(db_session)
    for class_name in ["fire_alarm", "fire_alarm", "doorbell"]:
        event = Event(
            device_id=device.id,
            class_name=class_name,
            confidence=0.9,
            duration=2.0,
            timestamp=datetime.now(timezone.utc),
        )
        db_session.add(event)
    await db_session.commit()

    resp = await client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["events_today"] == 3
    assert body["events_this_week"] == 3
    assert body["most_active_class"] == "fire_alarm"
    assert body["active_device_count"] == 1


@pytest.mark.anyio
async def test_dashboard_summary_counts_rules(client, db_session):
    rule = Rule(trigger="doorbell", priority="warn", alert_type="led")
    db_session.add(rule)
    await db_session.commit()

    resp = await client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    assert resp.json()["active_rule_count"] == 1
