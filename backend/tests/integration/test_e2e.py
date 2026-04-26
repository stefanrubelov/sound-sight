"""Phase 14 — Integration tests.

Covers the automatable items from the Phase 14 checklist:
  - E2E classify pipeline: PCM → event persisted + WebSocket broadcast
  - LLM pipeline: event created → llm_summary written by background task
  - Daily report: seeded events → GET /api/reports/daily returns narrative
  - Rule parsing via API: source_text → structured Rule persisted in DB
  - Anomaly narration: long-duration event + baseline → narration references baseline
  - Unknown sound: classified as 'unknown' → no alert, no LLM summary task

Hardware-dependent items (real ESP32, network drop) are covered by the
manual checklist in firmware/TESTING.md.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.db.models import Baseline, Event, Rule
from app.services.ml import classifier as clf_module

SAMPLE_RATE = 16000


# ── Helpers ───────────────────────────────────────────────────────────────────


def _fake_pcm(duration_s: float = 1.0) -> bytes:
    n = int(duration_s * SAMPLE_RATE)
    return (np.random.randn(n) * 0.5 * 32768).astype("int16").tobytes()


def _make_mock_classifier(class_name: str = "doorbell", confidence: float = 0.85):
    from ml.inference import ClassificationResult

    mock = MagicMock()
    mock.predict.return_value = ClassificationResult(
        class_name=class_name,
        confidence=confidence,
        all_scores={class_name: confidence, "unknown": 1.0 - confidence},
    )
    return mock


def _patch_session(db_session):
    """Patch AsyncSessionLocal so background tasks use the in-memory test DB."""

    class _Factory:
        def __call__(self):
            return self._ctx()

        @asynccontextmanager
        async def _ctx(self):
            yield db_session

    return patch("app.db.session.AsyncSessionLocal", new=_Factory())


# ── 1. E2E classify: event persisted + WebSocket broadcast fired ──────────────


@pytest.mark.anyio
async def test_e2e_classify_persists_and_broadcasts(client, db_session):
    """POST /api/audio/classify → event saved in DB and WS broadcast contains correct fields."""
    from sqlalchemy import select

    broadcast_calls: list[dict] = []

    async def _capture(payload: dict) -> None:
        broadcast_calls.append(payload)

    with patch.object(clf_module, "_classifier", _make_mock_classifier("doorbell", 0.88)):
        with patch("app.api.audio.ws_manager.broadcast", side_effect=_capture):
            with patch("app.api.audio._write_llm_summary", new=AsyncMock()):
                resp = await client.post(
                    "/api/audio/classify",
                    content=_fake_pcm(),
                    headers={"Content-Type": "application/octet-stream"},
                )

    assert resp.status_code == 200
    body = resp.json()
    assert body["class_name"] == "doorbell"

    # Event persisted
    result = await db_session.execute(select(Event).where(Event.id == body["event_id"]))
    event = result.scalar_one_or_none()
    assert event is not None
    assert event.class_name == "doorbell"
    assert event.confidence == pytest.approx(0.88)

    # WS broadcast fired with correct payload shape
    assert len(broadcast_calls) == 1
    ws = broadcast_calls[0]
    assert ws["event_id"] == body["event_id"]
    assert ws["class_name"] == "doorbell"
    assert ws["severity"] == body["severity"]
    assert "timestamp" in ws
    assert "led_color" in ws
    assert "vibration_pattern" in ws


# ── 2. LLM pipeline: background task writes llm_summary ──────────────────────


@pytest.mark.anyio
async def test_e2e_llm_summary_written(db_session):
    """_write_llm_summary populates Event.llm_summary after a real event is persisted."""
    from app.api.audio import _write_llm_summary

    event = Event(
        device_id=0,
        class_name="fire_alarm",
        confidence=0.91,
        duration=2.3,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    event_id = event.id

    expected_summary = "A fire alarm sounded in unknown room for 2.3 seconds."

    with _patch_session(db_session):
        with patch(
            "app.services.llm.chains.summarise_event",
            new=AsyncMock(return_value=expected_summary),
        ):
            with patch(
                "app.services.llm.agents.check_and_narrate_anomaly",
                new=AsyncMock(return_value=None),
            ):
                await _write_llm_summary(event_id, "fire_alarm")

    await db_session.refresh(event)
    assert event.llm_summary == expected_summary


# ── 3. Daily report: seeded events → endpoint returns narrative ───────────────


@pytest.mark.anyio
async def test_e2e_daily_report_with_seeded_events(client, db_session):
    """Seed events in DB, GET /api/reports/daily → structured ReportResponse with narrative."""
    from app.services.llm.agents import invalidate_cache

    now = datetime.now(timezone.utc)
    for class_name, confidence in [
        ("doorbell", 0.90),
        ("fire_alarm", 0.95),
        ("dog_barking", 0.70),
    ]:
        db_session.add(
            Event(
                device_id=0,
                class_name=class_name,
                confidence=confidence,
                duration=1.5,
                timestamp=now,
            )
        )
    await db_session.commit()
    invalidate_cache("daily")

    narrative = (
        "Today 3 sound events were recorded: a doorbell ring, a fire alarm, and dog barking. "
        "The fire alarm may warrant a check of smoke detectors. No unusual patterns were detected."
    )

    with patch("app.services.llm.agents.generate_report", new=AsyncMock(return_value=narrative)):
        resp = await client.get("/api/reports/daily")

    assert resp.status_code == 200
    body = resp.json()
    assert body["report_type"] == "daily"
    assert body["content"] == narrative
    assert len(body["content"]) > 50


# ── 4. Rule parsing via API: source_text → structured Rule persisted ──────────


@pytest.mark.anyio
async def test_e2e_rule_parsing_via_api(client, db_session):
    """POST /api/rules with source_text → LLM parses it → Rule row with correct fields."""
    from sqlalchemy import select

    from app.services.llm.chains.rule_parser import ParsedRule

    parsed = ParsedRule(
        trigger="glass_breaking",
        priority="critical",
        alert_type="vibration",
        time_start="22:00",
        time_end="07:00",
    )

    with patch("app.services.llm.chains.parse_rule", new=AsyncMock(return_value=parsed)):
        resp = await client.post(
            "/api/rules",
            json={"source_text": "Vibrate urgently if glass breaks after 22:00"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["trigger"] == "glass_breaking"
    assert body["priority"] == "critical"
    assert body["alert_type"] == "vibration"
    # RuleRead uses `time` type; Pydantic serialises time(22,0) → "22:00:00"
    assert body["time_start"].startswith("22:00")
    assert body["time_end"].startswith("07:00")

    # Rule persisted in DB with the original natural-language text
    result = await db_session.execute(select(Rule).where(Rule.id == body["id"]))
    rule = result.scalar_one_or_none()
    assert rule is not None
    assert rule.trigger == "glass_breaking"
    assert rule.source_text == "Vibrate urgently if glass breaks after 22:00"


# ── 5. Anomaly narration: long-duration event → narration returned ────────────


@pytest.mark.anyio
async def test_e2e_anomaly_narration_references_baseline(db_session):
    """check_and_narrate_anomaly returns a narration when duration is >3σ above baseline."""
    from app.services.llm.agents.anomaly_narrator import check_and_narrate_anomaly

    # Baseline: fire_alarm typically lasts ~2s ± 0.5s
    baseline = Baseline(
        class_name="fire_alarm",
        stats_json=json.dumps(
            {"mean_duration": 2.0, "std_duration": 0.5, "mean_count_per_day": 1.0}
        ),
    )
    db_session.add(baseline)

    # duration=5.0s → (5.0 - 2.0) / 0.5 = 6σ — clearly anomalous
    event = Event(
        device_id=0,
        class_name="fire_alarm",
        confidence=0.93,
        duration=5.0,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    expected_narration = (
        "The fire alarm sounded for 5 seconds, much longer than the typical 2 seconds. "
        "This may indicate a real emergency — please investigate immediately."
    )

    # Use FakeListChatModel so the LCEL chain works without a live Ollama instance
    fake_llm = FakeListChatModel(responses=[expected_narration])

    with patch("app.services.llm.agents.anomaly_narrator.get_chat_model", return_value=fake_llm):
        narration = await check_and_narrate_anomaly(event, "living room", db_session)

    assert narration is not None
    # FakeListChatModel returns the response as the chain output
    assert len(narration) > 10
    # Sigma is 6 — well above threshold — so a narration must be produced
    assert narration == expected_narration


# ── 6. Unknown sound → no alert, LLM task never triggered ────────────────────


@pytest.mark.anyio
async def test_e2e_unknown_sound_no_alert_no_llm_task(client):
    """Classify 'unknown' → severity=none, vibration=none, _write_llm_summary never called."""
    llm_task_invoked = False

    async def _track(event_id: int, class_name: str) -> None:
        nonlocal llm_task_invoked
        llm_task_invoked = True

    with patch.object(clf_module, "_classifier", _make_mock_classifier("unknown", 0.20)):
        with patch("app.api.audio._write_llm_summary", side_effect=_track):
            resp = await client.post(
                "/api/audio/classify",
                content=_fake_pcm(),
                headers={"Content-Type": "application/octet-stream"},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["class_name"] == "unknown"
    assert body["severity"] == "none"
    assert body["vibration_pattern"] == "none"
    assert not llm_task_invoked, "_write_llm_summary must not be called for unknown events"
