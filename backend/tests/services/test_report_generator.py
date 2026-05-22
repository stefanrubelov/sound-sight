"""Tests for the report generator (FakeListChatModel + in-memory DB)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

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
# generate_report — direct-DB fallback path (MCP returns no tools)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_generate_report_returns_string(db_session):
    invalidate_cache()
    expected = "All quiet in your home during the past 24 hours."
    with (
        patch(
            "app.services.llm.agents.report_generator.get_chat_model",
            return_value=_fake_llm(expected),
        ),
        patch(
            "app.services.llm.agents.report_generator.get_mcp_tools",
            new=AsyncMock(return_value=[]),
        ),
    ):
        result = await generate_report(db_session, "daily")

    assert result == expected


@pytest.mark.anyio
async def test_generate_report_cached(db_session):
    invalidate_cache()
    expected = "Cached report text."
    with (
        patch(
            "app.services.llm.agents.report_generator.get_chat_model",
            return_value=_fake_llm(expected),
        ),
        patch(
            "app.services.llm.agents.report_generator.get_mcp_tools",
            new=AsyncMock(return_value=[]),
        ),
    ):
        first = await generate_report(db_session, "daily")
        second = await generate_report(db_session, "daily")

    assert first == second == expected


@pytest.mark.anyio
async def test_generate_weekly_report(db_session):
    invalidate_cache()
    expected = "Weekly summary: a calm week overall."
    with (
        patch(
            "app.services.llm.agents.report_generator.get_chat_model",
            return_value=_fake_llm(expected),
        ),
        patch(
            "app.services.llm.agents.report_generator.get_mcp_tools",
            new=AsyncMock(return_value=[]),
        ),
    ):
        result = await generate_report(db_session, "weekly")

    assert result == expected


# ---------------------------------------------------------------------------
# generate_report — MCP agent path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_generate_report_uses_mcp_agent_when_tools_available(db_session):
    """When get_mcp_tools returns tools, the create_agent-backed path is used."""
    invalidate_cache()
    expected = "A quiet day with one doorbell event detected."

    from langchain_core.messages import AIMessage
    from langchain_core.tools import tool as lc_tool

    @lc_tool
    def query_events(limit: int = 20) -> list:  # noqa: ARG001
        """Query sound detection events."""
        return []

    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content=expected)]})

    with (
        patch(
            "app.services.llm.agents.report_generator.get_mcp_tools",
            new=AsyncMock(return_value=[query_events]),
        ),
        patch(
            "app.services.llm.agents.report_generator.create_agent",
            return_value=mock_agent,
        ),
        patch(
            "app.services.llm.agents.report_generator.get_chat_model",
            return_value=_fake_llm(expected),
        ),
    ):
        result = await generate_report(db_session, "daily")

    assert result == expected
    mock_agent.ainvoke.assert_called_once()


@pytest.mark.anyio
async def test_generate_report_falls_back_on_agent_failure(db_session):
    """If the MCP agent raises, generate_report returns the event-count fallback string."""
    invalidate_cache()

    from langchain_core.tools import tool as lc_tool

    @lc_tool
    def query_events(limit: int = 20) -> list:  # noqa: ARG001
        """Query sound detection events."""
        return []

    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(side_effect=RuntimeError("agent exploded"))

    with (
        patch(
            "app.services.llm.agents.report_generator.get_mcp_tools",
            new=AsyncMock(return_value=[query_events]),
        ),
        patch(
            "app.services.llm.agents.report_generator.create_agent",
            return_value=mock_agent,
        ),
        patch(
            "app.services.llm.agents.report_generator.get_chat_model",
            return_value=_fake_llm("irrelevant"),
        ),
    ):
        result = await generate_report(db_session, "daily")

    assert "Activity report" in result
    assert "recorded" in result
