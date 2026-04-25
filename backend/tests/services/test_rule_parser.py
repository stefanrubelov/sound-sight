"""Tests for the rule parser chain (FakeListChatModel)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.services.llm.chains.rule_parser import ParsedRule, parse_rule


def _fake_llm(*responses: str) -> FakeListChatModel:
    return FakeListChatModel(responses=list(responses))


# ---------------------------------------------------------------------------
# ParsedRule validators (no LLM needed)
# ---------------------------------------------------------------------------


def test_parsed_rule_normalises_trigger():
    r = ParsedRule(trigger="Fire Alarm")
    assert r.trigger == "fire_alarm"


def test_parsed_rule_unknown_trigger_fallback():
    r = ParsedRule(trigger="chainsaw")
    assert r.trigger == "unknown"


def test_parsed_rule_normalises_priority():
    r = ParsedRule(trigger="doorbell", priority="CRITICAL")
    assert r.priority == "critical"


def test_parsed_rule_invalid_priority_fallback():
    r = ParsedRule(trigger="doorbell", priority="extreme")
    assert r.priority == "warn"


def test_parsed_rule_normalises_time():
    r = ParsedRule(trigger="doorbell", time_start="9:30", time_end="17:00")
    assert r.time_start == "09:30"
    assert r.time_end == "17:00"


def test_parsed_rule_null_time_strings():
    r = ParsedRule(trigger="doorbell", time_start="null", time_end="none")
    assert r.time_start is None
    assert r.time_end is None


# ---------------------------------------------------------------------------
# Chain integration (FakeListChatModel)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_parse_rule_doorbell():
    raw = json.dumps(
        {
            "trigger": "doorbell",
            "priority": "warn",
            "alert_type": "vibration",
            "time_start": None,
            "time_end": None,
        }
    )
    with patch("app.services.llm.chains.rule_parser.get_chat_model", return_value=_fake_llm(raw)):
        result = await parse_rule("Vibrate when the doorbell rings")

    assert result.trigger == "doorbell"
    assert result.alert_type == "vibration"
    assert result.time_start is None


@pytest.mark.anyio
async def test_parse_rule_fire_alarm_at_night():
    raw = json.dumps(
        {
            "trigger": "fire_alarm",
            "priority": "critical",
            "alert_type": "both",
            "time_start": "22:00",
            "time_end": "07:00",
        }
    )
    with patch("app.services.llm.chains.rule_parser.get_chat_model", return_value=_fake_llm(raw)):
        result = await parse_rule("Alert me if the fire alarm goes off at night")

    assert result.trigger == "fire_alarm"
    assert result.priority == "critical"
    assert result.time_start == "22:00"
    assert result.time_end == "07:00"


@pytest.mark.anyio
async def test_parse_rule_ignore_water():
    raw = json.dumps(
        {
            "trigger": "water_running",
            "priority": "none",
            "alert_type": "none",
            "time_start": None,
            "time_end": None,
        }
    )
    with patch("app.services.llm.chains.rule_parser.get_chat_model", return_value=_fake_llm(raw)):
        result = await parse_rule("Ignore water running sounds")

    assert result.trigger == "water_running"
    assert result.priority == "none"
    assert result.alert_type == "none"


@pytest.mark.anyio
async def test_parse_rule_invalid_trigger_clamped_by_validator():
    raw = json.dumps(
        {
            "trigger": "mystery_sound",
            "priority": "ultra",
            "alert_type": "siren",
            "time_start": None,
            "time_end": None,
        }
    )
    with patch("app.services.llm.chains.rule_parser.get_chat_model", return_value=_fake_llm(raw)):
        result = await parse_rule("make a siren for mystery sounds")

    assert result.trigger == "unknown"
    assert result.priority == "warn"
    assert result.alert_type == "led"
