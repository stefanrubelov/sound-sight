"""Tests for POST /api/dev/inject_event."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_inject_event_returns_201_shape(client):
    with patch("app.api.dev._write_llm_summary", new=AsyncMock()):
        resp = await client.post(
            "/api/dev/inject_event",
            json={"class_name": "doorbell", "confidence": 0.91, "device_id": 1, "duration": 1.2},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["class_name"] == "doorbell"
    assert body["confidence"] == pytest.approx(0.91)
    assert body["severity"] == "warn"
    assert body["led_color"] == "#0000FF"
    assert body["vibration_pattern"] == "double_pulse"
    assert "event_id" in body


@pytest.mark.anyio
async def test_inject_event_persists_to_db(client, db_session):
    from sqlalchemy import select

    from app.db.models import Event

    with patch("app.api.dev._write_llm_summary", new=AsyncMock()):
        resp = await client.post(
            "/api/dev/inject_event",
            json={"class_name": "fire_alarm", "confidence": 0.95, "device_id": 2, "duration": 3.0},
        )
    assert resp.status_code == 200
    event_id = resp.json()["event_id"]

    result = await db_session.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    assert event is not None
    assert event.class_name == "fire_alarm"
    assert event.device_id == 2
    assert event.duration == pytest.approx(3.0)


@pytest.mark.anyio
async def test_inject_event_broadcasts_ws(client):
    broadcast_calls: list[dict] = []

    async def _capture(payload: dict) -> None:
        broadcast_calls.append(payload)

    with patch("app.api.dev.ws_manager.broadcast", side_effect=_capture):
        with patch("app.api.dev._write_llm_summary", new=AsyncMock()):
            resp = await client.post(
                "/api/dev/inject_event",
                json={"class_name": "glass_breaking", "confidence": 0.88, "device_id": 1},
            )

    assert resp.status_code == 200
    assert len(broadcast_calls) == 1
    ws = broadcast_calls[0]
    assert ws["class_name"] == "glass_breaking"
    assert ws["severity"] == "critical"
    assert "timestamp" in ws


@pytest.mark.anyio
async def test_inject_event_unknown_class_clamped(client):
    with patch("app.api.dev._write_llm_summary", new=AsyncMock()):
        resp = await client.post(
            "/api/dev/inject_event",
            json={"class_name": "chainsaw", "confidence": 0.80, "device_id": 1},
        )
    assert resp.status_code == 200
    assert resp.json()["class_name"] == "unknown"
    assert resp.json()["severity"] == "none"


@pytest.mark.anyio
async def test_inject_event_with_prewritten_summary_skips_llm(client, db_session):
    """When llm_summary is provided, the LLM background task must not be called."""
    from sqlalchemy import select

    from app.db.models import Event

    llm_called = False

    async def _track(*_a, **_kw) -> None:
        nonlocal llm_called
        llm_called = True

    with patch("app.api.dev._write_llm_summary", side_effect=_track):
        resp = await client.post(
            "/api/dev/inject_event",
            json={
                "class_name": "doorbell",
                "confidence": 0.90,
                "device_id": 1,
                "llm_summary": "Someone is at the door.",
            },
        )

    assert resp.status_code == 200
    assert not llm_called

    event_id = resp.json()["event_id"]
    result = await db_session.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    assert event is not None
    assert event.llm_summary == "Someone is at the door."


# ---------------------------------------------------------------------------
# Sad paths
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_inject_event_invalid_confidence_returns_422(client):
    resp = await client.post(
        "/api/dev/inject_event",
        json={"class_name": "doorbell", "confidence": 1.5},
    )
    assert resp.status_code == 422
