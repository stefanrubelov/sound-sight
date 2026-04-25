"""Tests for POST /api/onboarding/profile."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm.chains.onboarding_profiler import SoundProfile

_MOCK_PROFILE = SoundProfile(
    enabled_classes=["fire_alarm", "doorbell", "glass_breaking"],
    priorities={
        "fire_alarm": "critical",
        "doorbell": "warn",
        "glass_breaking": "critical",
    },
    quiet_hours_default=None,
)


@pytest.mark.anyio
async def test_onboarding_profile_creates_user_profile(client, db_session):
    from sqlalchemy import select

    from app.db.models import UserProfile

    with patch("app.services.llm.chains.build_profile", new=AsyncMock(return_value=_MOCK_PROFILE)):
        resp = await client.post(
            "/api/onboarding/profile",
            json={"home_description": "I live alone in a small flat."},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "fire_alarm" in body["enabled_classes"]
    assert body["priorities"]["fire_alarm"] == "critical"
    assert "profile_id" in body

    result = await db_session.execute(select(UserProfile))
    profile = result.scalar_one_or_none()
    assert profile is not None
    assert "fire_alarm" in profile.enabled_classes


@pytest.mark.anyio
async def test_onboarding_profile_with_quiet_hours(client):
    mock_profile = SoundProfile(
        enabled_classes=["fire_alarm", "baby_crying"],
        priorities={"fire_alarm": "critical", "baby_crying": "critical"},
        quiet_hours_default={"start": "22:00", "end": "07:00"},
    )
    with patch("app.services.llm.chains.build_profile", new=AsyncMock(return_value=mock_profile)):
        resp = await client.post(
            "/api/onboarding/profile",
            json={"home_description": "Family with a newborn baby, both parents deaf."},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["quiet_hours_default"] == {"start": "22:00", "end": "07:00"}


@pytest.mark.anyio
async def test_onboarding_short_description_returns_422(client):
    resp = await client.post(
        "/api/onboarding/profile",
        json={"home_description": "hi"},
    )
    assert resp.status_code == 422
