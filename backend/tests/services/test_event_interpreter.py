"""Tests for the event interpretation chain (FakeListChatModel)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.services.llm.chains.event_interpreter import interpret_event


def _fake_llm(response: str) -> FakeListChatModel:
    return FakeListChatModel(responses=[response])


@pytest.mark.anyio
async def test_interpret_event_returns_string():
    expected = "A fire alarm sounded in the hallway for 5.0 seconds."
    with patch(
        "app.services.llm.chains.event_interpreter.get_chat_model",
        return_value=_fake_llm(expected),
    ):
        result = await interpret_event(
            class_name="fire_alarm",
            confidence=0.92,
            duration=5.0,
            device_name="hall sensor",
            room="hallway",
            timestamp="2025-04-25T10:00:00Z",
        )
    assert result == expected


@pytest.mark.anyio
async def test_interpret_event_strips_whitespace():
    with patch(
        "app.services.llm.chains.event_interpreter.get_chat_model",
        return_value=_fake_llm("  The doorbell rang.  \n"),
    ):
        result = await interpret_event(
            class_name="doorbell",
            confidence=0.9,
            duration=1.0,
            room="front door",
        )
    assert result == "The doorbell rang."


@pytest.mark.anyio
async def test_interpret_event_with_user_notes():
    expected = "Baby crying detected — check the nursery."
    with patch(
        "app.services.llm.chains.event_interpreter.get_chat_model",
        return_value=_fake_llm(expected),
    ):
        result = await interpret_event(
            class_name="baby_crying",
            confidence=0.88,
            duration=12.0,
            device_name="nursery sensor",
            room="nursery",
            timestamp="",
            user_notes="Baby usually sleeps until 7am.",
        )
    assert "baby" in result.lower() or "nursery" in result.lower()
