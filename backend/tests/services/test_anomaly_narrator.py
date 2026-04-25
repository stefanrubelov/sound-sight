"""Tests for the anomaly narrator (FakeListChatModel + in-memory DB)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.db.models import Baseline, Event
from app.services.llm.agents.anomaly_narrator import check_and_narrate_anomaly


def _fake_llm(text: str) -> FakeListChatModel:
    return FakeListChatModel(responses=[text])


def _make_event(class_name: str = "fire_alarm", duration: float = 30.0) -> Event:
    e = Event()
    e.id = 99
    e.class_name = class_name
    e.confidence = 0.9
    e.duration = duration
    e.timestamp = datetime.now(timezone.utc)
    e.device_id = 0
    return e


def _make_baseline(class_name: str, mean_dur: float, std_dur: float) -> Baseline:
    b = Baseline()
    b.class_name = class_name
    b.stats_json = json.dumps({"mean_duration": mean_dur, "std_duration": std_dur})
    b.updated_at = datetime.now(timezone.utc)
    return b


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_no_baseline_returns_none(db_session):
    event = _make_event("fire_alarm", 30.0)
    result = await check_and_narrate_anomaly(event, "kitchen", db_session)
    assert result is None


@pytest.mark.anyio
async def test_normal_duration_returns_none(db_session):
    baseline = _make_baseline("fire_alarm", mean_dur=5.0, std_dur=2.0)
    db_session.add(baseline)
    await db_session.commit()

    # 7s is only 1σ above mean — not anomalous
    event = _make_event("fire_alarm", duration=7.0)
    result = await check_and_narrate_anomaly(event, "hall", db_session)
    assert result is None


@pytest.mark.anyio
async def test_anomalous_duration_triggers_narration(db_session):
    baseline = _make_baseline("fire_alarm", mean_dur=5.0, std_dur=2.0)
    db_session.add(baseline)
    await db_session.commit()

    narration = "The fire alarm rang for an unusually long time. Check your home."
    with patch(
        "app.services.llm.agents.anomaly_narrator.get_chat_model",
        return_value=_fake_llm(narration),
    ):
        # 17s = mean + 6σ — clearly anomalous
        event = _make_event("fire_alarm", duration=17.0)
        result = await check_and_narrate_anomaly(event, "hall", db_session)

    assert result == narration


@pytest.mark.anyio
async def test_zero_std_returns_none(db_session):
    baseline = _make_baseline("timer_beep", mean_dur=1.0, std_dur=0.0)
    db_session.add(baseline)
    await db_session.commit()

    event = _make_event("timer_beep", duration=100.0)
    result = await check_and_narrate_anomaly(event, "kitchen", db_session)
    assert result is None


@pytest.mark.anyio
async def test_boundary_exactly_three_sigma_not_anomalous(db_session):
    baseline = _make_baseline("dog_barking", mean_dur=5.0, std_dur=2.0)
    db_session.add(baseline)
    await db_session.commit()

    # Exactly 3σ above → threshold is > 3σ, so this should NOT trigger
    event = _make_event("dog_barking", duration=11.0)  # 5 + 3*2 = 11
    result = await check_and_narrate_anomaly(event, "garden", db_session)
    assert result is None
