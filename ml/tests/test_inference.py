"""Unit tests for ml/inference.py — mock model, fake PCM input."""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from ml.inference import Classifier, ClassificationResult, UNKNOWN_THRESHOLD
from ml.preprocess import SAMPLE_RATE, TARGET_CLASSES


def _make_proba(top_class_idx: int, top_conf: float) -> np.ndarray:
    """Build a probability array with the given class at top_conf, rest spread evenly."""
    n = len(TARGET_CLASSES)
    remaining = (1.0 - top_conf) / (n - 1)
    proba = np.full(n, remaining)
    proba[top_class_idx] = top_conf
    return proba


def _fake_pcm(duration_s: float = 1.0, amplitude: float = 0.5) -> bytes:
    n = int(duration_s * SAMPLE_RATE)
    samples = (np.random.randn(n) * amplitude * 32768).astype(np.int16)
    return samples.tobytes()


@pytest.fixture
def mock_clf():
    """Return a Classifier with a mocked sklearn model (no disk I/O)."""
    with patch("ml.inference.joblib.load") as mock_load:
        model = MagicMock()
        model.predict_proba.return_value = np.tile(
            _make_proba(top_class_idx=0, top_conf=0.85), (1, 1)
        )
        mock_load.return_value = model
        clf = Classifier(model_path="fake_path.joblib", threshold=UNKNOWN_THRESHOLD)
        clf._model = model
        yield clf, model


class TestClassificationResult:
    def test_fields(self):
        r = ClassificationResult(
            class_name="dog_barking",
            confidence=0.9,
            all_scores={"dog_barking": 0.9},
        )
        assert r.class_name == "dog_barking"
        assert r.confidence == 0.9
        assert r.all_scores["dog_barking"] == 0.9

    def test_default_all_scores(self):
        r = ClassificationResult(class_name="unknown", confidence=0.0)
        assert r.all_scores == {}


class TestClassifier:
    def test_predict_returns_result(self, mock_clf):
        clf, model = mock_clf
        proba = np.tile(_make_proba(0, 0.85), (2, 1))
        model.predict_proba.return_value = proba

        result = clf.predict(_fake_pcm())
        assert isinstance(result, ClassificationResult)
        assert result.class_name in TARGET_CLASSES + ["unknown"]
        assert 0.0 <= result.confidence <= 1.0

    def test_all_scores_sum_near_one(self, mock_clf):
        clf, model = mock_clf
        proba = np.tile(_make_proba(0, 0.85), (2, 1))
        model.predict_proba.return_value = proba

        result = clf.predict(_fake_pcm())
        total = sum(result.all_scores.values())
        assert abs(total - 1.0) < 1e-5, f"Scores sum to {total}"

    def test_all_scores_keys_match_classes(self, mock_clf):
        clf, model = mock_clf
        proba = np.tile(_make_proba(0, 0.85), (2, 1))
        model.predict_proba.return_value = proba

        result = clf.predict(_fake_pcm())
        assert set(result.all_scores.keys()) == set(TARGET_CLASSES)

    def test_low_confidence_returns_unknown(self, mock_clf):
        clf, model = mock_clf
        # top confidence below threshold → unknown
        low_conf_proba = np.tile(_make_proba(0, 0.30), (2, 1))
        model.predict_proba.return_value = low_conf_proba

        result = clf.predict(_fake_pcm())
        assert result.class_name == "unknown"

    def test_high_confidence_returns_class(self, mock_clf):
        clf, model = mock_clf
        fire_idx = TARGET_CLASSES.index("fire_alarm")
        high_conf_proba = np.tile(_make_proba(fire_idx, 0.92), (2, 1))
        model.predict_proba.return_value = high_conf_proba

        result = clf.predict(_fake_pcm())
        assert result.class_name == "fire_alarm"
        assert result.confidence > 0.9

    def test_empty_audio_returns_unknown(self, mock_clf):
        clf, _ = mock_clf
        # Zero-length bytes → unknown
        result = clf.predict(b"")
        assert result.class_name == "unknown"
        assert result.confidence == 0.0

    def test_confidence_matches_top_score(self, mock_clf):
        clf, model = mock_clf
        dog_idx = TARGET_CLASSES.index("dog_barking")
        proba_row = _make_proba(dog_idx, 0.80)
        model.predict_proba.return_value = np.tile(proba_row, (2, 1))

        result = clf.predict(_fake_pcm())
        if result.class_name != "unknown":
            assert abs(result.confidence - result.all_scores[result.class_name]) < 1e-5
