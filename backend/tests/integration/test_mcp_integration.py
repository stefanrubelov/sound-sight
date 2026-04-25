"""Integration test: LangChain agent → MCP tools → DB.

Calls MCP tools through FastMCP.call_tool() (in-process, no HTTP) so the test
does not require a live server.  Verifies the full pipeline:
  agent selects a tool → tool queries the test DB → result returned to agent.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.db.models import Event, Rule, UserProfile
from app.mcp.server import mcp


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _patch_db(db_session):
    """Return a context manager that patches AsyncSessionLocal in the MCP server."""

    class _Factory:
        def __call__(self):
            return self._ctx()

        @asynccontextmanager
        async def _ctx(self):
            yield db_session

    return patch("app.mcp.server.AsyncSessionLocal", new=_Factory())


def _extract(call_result) -> object:
    """Parse the structured result from call_tool's return value.

    FastMCP returns:
    - (list[TextContent], {'result': [...]})  for list[dict] return types
    - list[TextContent]                        for plain dict return types
    """
    if isinstance(call_result, tuple):
        _, result_dict = call_result
        return result_dict.get("result")
    # plain dict: first content block holds the full JSON
    text = call_result[0].text if call_result else "{}"
    return json.loads(text)


# ── MCP tool schema / listing ─────────────────────────────────────────────────


@pytest.mark.anyio
async def test_mcp_tools_have_descriptions():
    tools = await mcp.list_tools()
    for tool in tools:
        assert tool.description, f"Tool '{tool.name}' has no description"
        assert tool.inputSchema, f"Tool '{tool.name}' has no input schema"


@pytest.mark.anyio
async def test_mcp_tool_names_are_valid_identifiers():
    tools = await mcp.list_tools()
    for t in tools:
        assert t.name.isidentifier(), f"'{t.name}' is not a valid Python identifier"


# ── call_tool in-process ──────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_call_query_events_via_mcp(db_session):
    event = Event(
        device_id=0,
        class_name="glass_breaking",
        confidence=0.95,
        duration=0.8,
        timestamp=_now(),
    )
    db_session.add(event)
    await db_session.commit()

    with _patch_db(db_session):
        raw = await mcp.call_tool("query_events", {"class_name": "glass_breaking"})

    events = _extract(raw)
    assert isinstance(events, list)
    assert len(events) >= 1
    assert events[0]["class_name"] == "glass_breaking"


@pytest.mark.anyio
async def test_call_get_user_profile_via_mcp(db_session):
    profile = UserProfile(
        home_description="Test home.",
        enabled_classes=json.dumps(["fire_alarm", "doorbell"]),
    )
    db_session.add(profile)
    await db_session.commit()

    with _patch_db(db_session):
        raw = await mcp.call_tool("get_user_profile", {})

    result = _extract(raw)
    assert result is not None
    assert "fire_alarm" in result.get("enabled_classes", [])


@pytest.mark.anyio
async def test_call_get_sound_class_info_via_mcp():
    raw = await mcp.call_tool("get_sound_class_info", {"class_name": "doorbell"})
    result = _extract(raw)
    assert result is not None
    assert result.get("class_name") == "doorbell"
    assert "content" in result


@pytest.mark.anyio
async def test_call_get_active_rules_via_mcp(db_session):
    rule = Rule(trigger="doorbell", priority="warn", alert_type="vibration")
    db_session.add(rule)
    await db_session.commit()

    with _patch_db(db_session):
        raw = await mcp.call_tool("get_active_rules", {})

    rules = _extract(raw)
    assert isinstance(rules, list)
    assert len(rules) == 1
    assert rules[0]["trigger"] == "doorbell"
