"""
Inference wrapper — shared between ml/ scripts and the FastAPI backend.

Usage:
    clf = Classifier()
    result = clf.predict(pcm_bytes)
    # result.class_name, result.confidence, result.all_scores
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import joblib
import numpy as np

from ml.preprocess import (
    SAMPLE_RATE,
    TARGET_CLASSES,
    extract_mfcc,
    pcm_bytes_to_audio,
    window_audio,
)

log = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = Path(__file__).parent / "artifacts" / "soundsight_classifier.joblib"
UNKNOWN_THRESHOLD = 0.50


@dataclass
class ClassificationResult:
    class_name: str
    confidence: float
    all_scores: dict[str, float] = field(default_factory=dict)


class Classifier:
    """Wraps a trained sklearn model for real-time PCM inference."""

    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        threshold: float = UNKNOWN_THRESHOLD,
    ) -> None:
        self._threshold = threshold
        self._model = joblib.load(str(model_path))
        log.info("Loaded classifier from %s (threshold=%.2f)", model_path, threshold)

    def predict(self, pcm_bytes: bytes, sample_rate: int = SAMPLE_RATE) -> ClassificationResult:
        """Classify raw 16-bit signed PCM audio bytes.

        Applies the same MFCC preprocessing used during training.
        Returns `class_name="unknown"` when top confidence < threshold.
        """
        audio = pcm_bytes_to_audio(pcm_bytes, sample_rate)
        return self._predict_audio(audio, sample_rate)

    def predict_file(self, path: str | Path) -> ClassificationResult:
        """Convenience method: classify an audio file directly."""
        import librosa

        audio, sr = librosa.load(str(path), sr=SAMPLE_RATE, mono=True)
        return self._predict_audio(audio, sr)

    def _predict_audio(self, audio: np.ndarray, sr: int) -> ClassificationResult:
        clips = window_audio(audio, sr)
        # Discard windows that are more than 50% zero-padding — they produce
        # features the model was never trained on and drag everything toward unknown.
        clip_len = int(1.0 * sr)
        clips = [c for c in clips if np.count_nonzero(c) > clip_len * 0.5]
        if not clips:
            return ClassificationResult(
                class_name="unknown",
                confidence=0.0,
                all_scores={cls: 0.0 for cls in TARGET_CLASSES},
            )

        # Average predictions across all windows
        features = np.array([extract_mfcc(clip, sr) for clip in clips])
        proba = self._model.predict_proba(features).mean(axis=0)

        top_idx = int(proba.argmax())
        top_conf = float(proba[top_idx])
        top_class = TARGET_CLASSES[top_idx]

        if top_conf < self._threshold:
            top_class = "unknown"

        all_scores = {TARGET_CLASSES[i]: float(proba[i]) for i in range(len(TARGET_CLASSES))}

        return ClassificationResult(
            class_name=top_class,
            confidence=top_conf,
            all_scores=all_scores,
        )


_default_classifier: Optional[Classifier] = None


def get_classifier(
    model_path: str | Path = DEFAULT_MODEL_PATH,
    threshold: float = UNKNOWN_THRESHOLD,
) -> Classifier:
    """Return a module-level singleton classifier (lazy-loaded)."""
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = Classifier(model_path=model_path, threshold=threshold)
    return _default_classifier
