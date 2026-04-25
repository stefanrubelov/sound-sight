"""Tests for GET /api/settings and PUT /api/settings."""

from __future__ import annotations

import pytest

from app.db.models import UserProfile


async def _seed_profile(db_session, **kwargs) -> UserProfile:
    profile = UserProfile(**kwargs)
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


# ---------------------------------------------------------------------------
# GET /api/settings — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_settings_returns_profile(client, db_session):
    await _seed_profile(db_session, notes="Test notes", home_description="A cozy flat.")
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["notes"] == "Test notes"
    assert body["id"] > 0


# ---------------------------------------------------------------------------
# GET /api/settings — sad path: no profile
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_settings_no_profile_returns_404(client):
    resp = await client.get("/api/settings")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/settings — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_put_settings_updates_notes(client, db_session):
    await _seed_profile(db_session)
    resp = await client.put("/api/settings", json={"notes": "Updated notes"})
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Updated notes"


@pytest.mark.anyio
async def test_put_settings_updates_enabled_classes(client, db_session):
    await _seed_profile(db_session)
    resp = await client.put(
        "/api/settings",
        json={"enabled_classes": ["fire_alarm", "doorbell"]},
    )
    assert resp.status_code == 200
    assert resp.json()["enabled_classes"] == ["fire_alarm", "doorbell"]


@pytest.mark.anyio
async def test_put_settings_updates_quiet_hours(client, db_session):
    await _seed_profile(db_session)
    resp = await client.put(
        "/api/settings",
        json={"quiet_hours": {"start": "22:00", "end": "07:00"}},
    )
    assert resp.status_code == 200
    assert resp.json()["quiet_hours"] == {"start": "22:00", "end": "07:00"}


@pytest.mark.anyio
async def test_put_settings_creates_profile_if_missing(client):
    resp = await client.put("/api/settings", json={"notes": "Created via PUT"})
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Created via PUT"
    assert resp.json()["id"] > 0


# ---------------------------------------------------------------------------
# PUT /api/settings — sad path: invalid body
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_put_settings_invalid_body_returns_422(client):
    resp = await client.put("/api/settings", json={"enabled_classes": "not-a-list"})
    assert resp.status_code == 422
