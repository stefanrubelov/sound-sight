"""Tests for POST/GET /api/rules."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm.chains.rule_parser import ParsedRule


def _parsed_rule(**kwargs) -> ParsedRule:
    defaults = {
        "trigger": "doorbell",
        "priority": "warn",
        "alert_type": "vibration",
        "time_start": None,
        "time_end": None,
    }
    defaults.update(kwargs)
    return ParsedRule(**defaults)


# ---------------------------------------------------------------------------
# Structured body
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_rule_structured(client):
    resp = await client.post(
        "/api/rules",
        json={"trigger": "fire_alarm", "priority": "critical", "alert_type": "both"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["trigger"] == "fire_alarm"
    assert body["priority"] == "critical"
    assert body["id"] > 0


@pytest.mark.anyio
async def test_create_rule_nl_text(client):
    mock_parsed = _parsed_rule(trigger="doorbell", alert_type="vibration")
    with patch("app.services.llm.chains.parse_rule", new=AsyncMock(return_value=mock_parsed)):
        resp = await client.post(
            "/api/rules",
            json={"source_text": "Vibrate when the doorbell rings"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["trigger"] == "doorbell"
    assert body["source_text"] == "Vibrate when the doorbell rings"


@pytest.mark.anyio
async def test_create_rule_missing_both_fields_returns_422(client):
    resp = await client.post("/api/rules", json={"priority": "warn"})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_create_rule_nl_parse_error_returns_422(client):
    with patch(
        "app.services.llm.chains.parse_rule", new=AsyncMock(side_effect=ValueError("parse failed"))
    ):
        resp = await client.post(
            "/api/rules",
            json={"source_text": "do something impossible"},
        )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/rules
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_rules_empty(client):
    resp = await client.get("/api/rules")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_list_rules_after_create(client):
    await client.post(
        "/api/rules",
        json={"trigger": "timer_beep", "priority": "info", "alert_type": "led"},
    )
    resp = await client.get("/api/rules")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
