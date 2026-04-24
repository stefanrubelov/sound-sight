"""
Integration test: end-to-end pipeline on a known synthetic audio clip.

Generates a pure 440 Hz sine tone (a sound the model will classify as
something — exact class doesn't matter), trains a tiny model on-the-fly
using the mock infrastructure, and asserts the pipeline runs without error.

A real integration test would load the trained artifact and run on a held-out
.wav clip; that version is in conftest and gated by the HAS_MODEL marker.
"""

from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ml.preprocess import (
    SAMPLE_RATE,
    TARGET_CLASSES,
)
from ml.inference import Classifier, ClassificationResult


def _sine_pcm(freq: float = 440.0, duration: float = 1.0) -> bytes:
    """Generate a pure sine wave as 16-bit PCM bytes."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    wave = (np.sin(2 * np.pi * freq * t) * 32767 * 0.8).astype(np.int16)
    return wave.tobytes()


class TestEndToEndPipeline:
    """Run the full feature-extraction → inference chain on synthetic audio."""

    @patch("ml.inference.joblib.load")
    def test_pipeline_runs_without_error(self, mock_load):
        """Pipeline from PCM bytes to ClassificationResult, no real model needed."""
        n_classes = len(TARGET_CLASSES)
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = np.tile(
            np.ones(n_classes) / n_classes, (2, 1)
        )
        mock_load.return_value = mock_model

        clf = Classifier(model_path="fake.joblib", threshold=0.50)
        clf._model = mock_model

        pcm = _sine_pcm(freq=440.0, duration=1.5)
        result = clf.predict(pcm)

        assert isinstance(result, ClassificationResult)
        assert result.class_name in TARGET_CLASSES + ["unknown"]
        assert 0.0 <= result.confidence <= 1.0
        assert set(result.all_scores.keys()) == set(TARGET_CLASSES)

    @patch("ml.inference.joblib.load")
    def test_mfcc_features_passed_to_model(self, mock_load):
        """Verify the model receives correctly shaped MFCC features."""
        n_classes = len(TARGET_CLASSES)
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = np.zeros((1, n_classes))
        mock_model.predict_proba.return_value[0, 0] = 1.0
        mock_load.return_value = mock_model

        clf = Classifier(model_path="fake.joblib", threshold=0.50)
        clf._model = mock_model

        pcm = _sine_pcm(freq=880.0, duration=1.0)
        clf.predict(pcm)

        call_args = mock_model.predict_proba.call_args
        assert call_args is not None, "predict_proba was never called"
        X = call_args[0][0]
        assert X.ndim == 2, "Expected 2-D feature matrix"
        assert X.shape[1] == 80, f"Expected 80 MFCC features, got {X.shape[1]}"


@pytest.mark.skipif(
    not (
        Path(__file__).parents[1] / "artifacts" / "soundsight_classifier.joblib"
    ).exists(),
    reason="Trained model artifact not found — run ml/train.py first",
)
class TestWithRealModel:
    """Runs only when a trained model artifact exists."""

    def test_predict_known_clip(self, tmp_path):
        """Synthetic sine wave → model returns a valid ClassificationResult."""

        clf = Classifier()
        pcm = _sine_pcm(freq=440.0, duration=2.0)
        result = clf.predict(pcm)

        assert result.class_name in TARGET_CLASSES + ["unknown"]
        assert 0.0 <= result.confidence <= 1.0
        assert abs(sum(result.all_scores.values()) - 1.0) < 1e-4
