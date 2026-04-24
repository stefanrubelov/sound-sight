"""Tests for POST /api/audio/classify."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.ml import classifier as clf_module

SAMPLE_RATE = 16000


def _fake_pcm(duration_s: float = 1.0) -> bytes:
    n = int(duration_s * SAMPLE_RATE)
    return (np.random.randn(n) * 0.5 * 32768).astype("int16").tobytes()


def _make_mock_classifier(class_name: str = "dog_barking", confidence: float = 0.85):
    from ml.inference import ClassificationResult

    mock = MagicMock()
    mock.predict.return_value = ClassificationResult(
        class_name=class_name,
        confidence=confidence,
        all_scores={class_name: confidence, "unknown": 1.0 - confidence},
    )
    return mock


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_classify_returns_200(client):
    with patch.object(clf_module, "_classifier", _make_mock_classifier()):
        resp = await client.post(
            "/api/audio/classify",
            content=_fake_pcm(),
            headers={"Content-Type": "application/octet-stream"},
        )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_classify_response_schema(client):
    mock_clf = _make_mock_classifier("fire_alarm", 0.92)
    with patch.object(clf_module, "_classifier", mock_clf):
        resp = await client.post(
            "/api/audio/classify",
            content=_fake_pcm(),
            headers={"Content-Type": "application/octet-stream"},
        )
    body = resp.json()
    assert body["class_name"] == "fire_alarm"
    assert body["confidence"] == pytest.approx(0.92)
    assert body["severity"] == "critical"
    assert body["led_color"] == "#FF0000"
    assert body["vibration_pattern"] == "continuous"
    assert "event_id" in body
    assert "device_id" in body


@pytest.mark.anyio
async def test_classify_persists_event(client, db_session):
    from sqlalchemy import select

    from app.db.models import Event

    mock_clf = _make_mock_classifier("doorbell", 0.80)
    with patch.object(clf_module, "_classifier", mock_clf):
        resp = await client.post(
            "/api/audio/classify",
            content=_fake_pcm(),
            headers={"Content-Type": "application/octet-stream"},
        )
    assert resp.status_code == 200
    event_id = resp.json()["event_id"]

    result = await db_session.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    assert event is not None
    assert event.class_name == "doorbell"
    assert event.confidence == pytest.approx(0.80)


@pytest.mark.anyio
async def test_classify_severity_mapping(client):
    """Each class should map to the correct severity."""
    cases = [
        ("fire_alarm", "critical"),
        ("glass_breaking", "critical"),
        ("baby_crying", "warn"),
        ("doorbell", "warn"),
        ("dog_barking", "warn"),
        ("timer_beep", "info"),
        ("water_running", "info"),
        ("unknown", "none"),
    ]
    for class_name, expected_severity in cases:
        mock_clf = _make_mock_classifier(class_name, 0.90)
        with patch.object(clf_module, "_classifier", mock_clf):
            resp = await client.post(
                "/api/audio/classify",
                content=_fake_pcm(),
                headers={"Content-Type": "application/octet-stream"},
            )
        assert resp.json()["severity"] == expected_severity, f"Failed for {class_name}"


@pytest.mark.anyio
async def test_classify_unknown_no_vibration(client):
    mock_clf = _make_mock_classifier("unknown", 0.30)
    with patch.object(clf_module, "_classifier", mock_clf):
        resp = await client.post(
            "/api/audio/classify",
            content=_fake_pcm(),
            headers={"Content-Type": "application/octet-stream"},
        )
    body = resp.json()
    assert body["vibration_pattern"] == "none"
    assert body["severity"] == "none"


@pytest.mark.anyio
async def test_classify_raw_features_stored(client, db_session):
    from sqlalchemy import select

    from app.db.models import Event

    mock_clf = _make_mock_classifier("timer_beep", 0.75)
    with patch.object(clf_module, "_classifier", mock_clf):
        resp = await client.post(
            "/api/audio/classify",
            content=_fake_pcm(),
            headers={"Content-Type": "application/octet-stream"},
        )
    event_id = resp.json()["event_id"]
    result = await db_session.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one()
    assert event.raw_features is not None
    scores = json.loads(event.raw_features)
    assert "timer_beep" in scores


# ---------------------------------------------------------------------------
# Sad paths
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_classify_empty_body_returns_422(client):
    with patch.object(clf_module, "_classifier", _make_mock_classifier()):
        resp = await client.post(
            "/api/audio/classify",
            content=b"",
            headers={"Content-Type": "application/octet-stream"},
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_classify_no_model_returns_unknown(client):
    """When no model artifact is loaded, endpoint should still return 200 with unknown."""
    with patch.object(clf_module, "_classifier", None):
        with patch.object(clf_module, "get_classifier", return_value=None):
            resp = await client.post(
                "/api/audio/classify",
                content=_fake_pcm(),
                headers={"Content-Type": "application/octet-stream"},
            )
    assert resp.status_code == 200
    assert resp.json()["class_name"] == "unknown"
