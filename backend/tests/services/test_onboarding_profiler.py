"""Tests for the onboarding profiler chain (FakeListChatModel)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.services.llm.chains.onboarding_profiler import SoundProfile, build_profile


def _fake_llm(obj: dict) -> FakeListChatModel:
    return FakeListChatModel(responses=[json.dumps(obj)])


_SINGLE_PERSON_OUTPUT = {
    "enabled_classes": ["fire_alarm", "glass_breaking", "doorbell", "timer_beep"],
    "priorities": {
        "fire_alarm": "critical",
        "glass_breaking": "critical",
        "doorbell": "warn",
        "timer_beep": "info",
    },
    "quiet_hours_default": None,
}

_FAMILY_BABY_OUTPUT = {
    "enabled_classes": [
        "fire_alarm",
        "glass_breaking",
        "baby_crying",
        "doorbell",
        "dog_barking",
        "timer_beep",
    ],
    "priorities": {
        "fire_alarm": "critical",
        "glass_breaking": "critical",
        "baby_crying": "critical",
        "doorbell": "warn",
        "dog_barking": "info",
        "timer_beep": "info",
    },
    "quiet_hours_default": {"start": "22:00", "end": "07:00"},
}


@pytest.mark.anyio
async def test_build_profile_single_person():
    with patch(
        "app.services.llm.chains.onboarding_profiler.get_chat_model",
        return_value=_fake_llm(_SINGLE_PERSON_OUTPUT),
    ):
        profile = await build_profile("I live alone in a flat, no pets.")

    assert isinstance(profile, SoundProfile)
    assert "fire_alarm" in profile.enabled_classes
    assert profile.priorities["fire_alarm"] == "critical"
    assert profile.quiet_hours_default is None


@pytest.mark.anyio
async def test_build_profile_family_with_baby():
    with patch(
        "app.services.llm.chains.onboarding_profiler.get_chat_model",
        return_value=_fake_llm(_FAMILY_BABY_OUTPUT),
    ):
        profile = await build_profile(
            "We have a 6-month-old baby and a dog. Both parents are deaf."
        )

    assert "baby_crying" in profile.enabled_classes
    assert profile.priorities["baby_crying"] == "critical"
    assert profile.quiet_hours_default is not None
    assert profile.quiet_hours_default["start"] == "22:00"


@pytest.mark.anyio
async def test_build_profile_returns_correct_types():
    with patch(
        "app.services.llm.chains.onboarding_profiler.get_chat_model",
        return_value=_fake_llm(_SINGLE_PERSON_OUTPUT),
    ):
        profile = await build_profile("Small apartment, living alone.")

    assert isinstance(profile.enabled_classes, list)
    assert isinstance(profile.priorities, dict)
    assert all(isinstance(c, str) for c in profile.enabled_classes)
