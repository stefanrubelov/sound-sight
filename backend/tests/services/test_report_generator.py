"""Tests for the report generator (FakeListChatModel + in-memory DB)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.db.models import Event
from app.services.llm.agents.report_generator import (
    _fmt_baselines,
    _fmt_events,
    _fmt_rules,
    generate_report,
    invalidate_cache,
)


def _fake_llm(text: str) -> FakeListChatModel:
    return FakeListChatModel(responses=[text])


def _make_event(class_name: str = "doorbell", duration: float = 1.5) -> Event:
    e = Event()
    e.id = 1
    e.class_name = class_name
    e.confidence = 0.85
    e.duration = duration
    e.timestamp = datetime.now(timezone.utc)
    e.llm_summary = None
    e.device_id = 0
    return e


# ---------------------------------------------------------------------------
# Formatting helpers (pure, no DB)
# ---------------------------------------------------------------------------


def test_fmt_events_empty():
    assert "No events" in _fmt_events([])


def test_fmt_events_single():
    text = _fmt_events([_make_event("fire_alarm", 5.0)])
    assert "fire alarm" in text.lower()
    assert "5.0s" in text


def test_fmt_events_with_summary():
    e = _make_event()
    e.llm_summary = "The doorbell rang."
    text = _fmt_events([e])
    assert "The doorbell rang." in text


def test_fmt_rules_empty():
    assert "No active rules" in _fmt_rules([])


def test_fmt_baselines_empty():
    assert "No baseline" in _fmt_baselines([])


# ---------------------------------------------------------------------------
# generate_report (FakeListChatModel + DB fixture)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_generate_report_returns_string(db_session):
    invalidate_cache()
    expected = "All quiet in your home during the past 24 hours."
    with patch(
        "app.services.llm.agents.report_generator.get_chat_model",
        return_value=_fake_llm(expected),
    ):
        result = await generate_report(db_session, "daily")

    assert result == expected


@pytest.mark.anyio
async def test_generate_report_cached(db_session):
    invalidate_cache()
    expected = "Cached report text."
    with patch(
        "app.services.llm.agents.report_generator.get_chat_model",
        return_value=_fake_llm(expected),
    ):
        first = await generate_report(db_session, "daily")
        second = await generate_report(db_session, "daily")

    assert first == second == expected


@pytest.mark.anyio
async def test_generate_weekly_report(db_session):
    invalidate_cache()
    expected = "Weekly summary: a calm week overall."
    with patch(
        "app.services.llm.agents.report_generator.get_chat_model",
        return_value=_fake_llm(expected),
    ):
        result = await generate_report(db_session, "weekly")

    assert result == expected
