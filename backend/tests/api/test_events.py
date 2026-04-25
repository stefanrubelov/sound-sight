"""Tests for GET /api/events and POST /api/events/{id}/explain."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.db.models import Device, Event


async def _seed_device(db_session, name="Sensor-A", room="kitchen") -> Device:
    device = Device(name=name, room=room, registered_at=datetime.now(timezone.utc))
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


async def _seed_event(db_session, device: Device, class_name="fire_alarm", **kwargs) -> Event:
    event = Event(
        device_id=device.id,
        class_name=class_name,
        confidence=kwargs.get("confidence", 0.92),
        duration=kwargs.get("duration", 3.5),
        timestamp=kwargs.get("timestamp", datetime.now(timezone.utc)),
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


# ---------------------------------------------------------------------------
# GET /api/events — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_events_empty(client):
    resp = await client.get("/api/events")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_list_events_returns_seeded(client, db_session):
    device = await _seed_device(db_session)
    await _seed_event(db_session, device, "doorbell")
    resp = await client.get("/api/events")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["class_name"] == "doorbell"


@pytest.mark.anyio
async def test_list_events_filter_by_class(client, db_session):
    device = await _seed_device(db_session)
    await _seed_event(db_session, device, "fire_alarm")
    await _seed_event(db_session, device, "doorbell")
    resp = await client.get("/api/events", params={"class": "fire_alarm"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(e["class_name"] == "fire_alarm" for e in data)
    assert len(data) == 1


@pytest.mark.anyio
async def test_list_events_filter_by_room(client, db_session):
    kitchen = await _seed_device(db_session, name="Kitchen Sensor", room="kitchen")
    hallway = await _seed_device(db_session, name="Hallway Sensor", room="hallway")
    await _seed_event(db_session, kitchen, "fire_alarm")
    await _seed_event(db_session, hallway, "doorbell")
    resp = await client.get("/api/events", params={"room": "kitchen"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["class_name"] == "fire_alarm"


@pytest.mark.anyio
async def test_list_events_pagination(client, db_session):
    device = await _seed_device(db_session)
    for _ in range(5):
        await _seed_event(db_session, device)
    resp = await client.get("/api/events", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp2 = await client.get("/api/events", params={"limit": 2, "offset": 2})
    assert resp2.status_code == 200
    assert len(resp2.json()) == 2


# ---------------------------------------------------------------------------
# GET /api/events — sad paths
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_events_invalid_limit(client):
    resp = await client.get("/api/events", params={"limit": 0})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_list_events_invalid_offset(client):
    resp = await client.get("/api/events", params={"offset": -1})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/events/{id}/explain — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_explain_event_returns_summary(client, db_session):
    device = await _seed_device(db_session)
    event = await _seed_event(db_session, device, "glass_breaking")

    with patch(
        "app.services.llm.chains.summarise_event",
        new=AsyncMock(return_value="Glass breaking detected in kitchen for 3.5 seconds."),
    ):
        resp = await client.post(f"/api/events/{event.id}/explain")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == event.id
    assert "Glass breaking" in body["llm_summary"]


# ---------------------------------------------------------------------------
# POST /api/events/{id}/explain — sad paths
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_explain_event_not_found(client):
    resp = await client.post("/api/events/99999/explain")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_explain_event_llm_failure_returns_503(client, db_session):
    device = await _seed_device(db_session)
    event = await _seed_event(db_session, device, "doorbell")

    with patch(
        "app.services.llm.chains.summarise_event",
        new=AsyncMock(side_effect=RuntimeError("LLM unreachable")),
    ):
        resp = await client.post(f"/api/events/{event.id}/explain")

    assert resp.status_code == 503
