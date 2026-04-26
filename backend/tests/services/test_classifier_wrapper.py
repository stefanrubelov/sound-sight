"""Unit tests for app/services/ml/classifier.py — lazy-load wrapper."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.ml.classifier import get_classifier, reset_classifier


@pytest.fixture(autouse=True)
def clean_classifier():
    """Ensure module-level singleton is reset before and after each test."""
    reset_classifier()
    yield
    reset_classifier()


def test_returns_none_when_model_path_missing(tmp_path):
    with patch("app.services.ml.classifier.settings") as cfg:
        cfg.ml_model_path = str(tmp_path / "no_such_file.joblib")
        result = get_classifier()
    assert result is None


def test_returns_none_again_on_repeated_calls_without_model(tmp_path):
    with patch("app.services.ml.classifier.settings") as cfg:
        cfg.ml_model_path = str(tmp_path / "no_such_file.joblib")
        r1 = get_classifier()
        r2 = get_classifier()
    assert r1 is None
    assert r2 is None


def test_returns_singleton_when_model_loads(tmp_path):
    fake_path = tmp_path / "model.joblib"
    fake_path.touch()
    mock_instance = MagicMock()

    with patch("app.services.ml.classifier.settings") as cfg:
        cfg.ml_model_path = str(fake_path)
        cfg.ml_unknown_threshold = 0.5
        with patch("ml.inference.Classifier", return_value=mock_instance) as cls:
            first = get_classifier()
            second = get_classifier()

    assert first is second
    assert cls.call_count == 1


def test_reset_clears_cached_instance(tmp_path):
    fake_path = tmp_path / "model.joblib"
    fake_path.touch()
    mock_a = MagicMock()
    mock_b = MagicMock()

    with patch("app.services.ml.classifier.settings") as cfg:
        cfg.ml_model_path = str(fake_path)
        cfg.ml_unknown_threshold = 0.5
        with patch("ml.inference.Classifier", side_effect=[mock_a, mock_b]):
            first = get_classifier()
            reset_classifier()
            second = get_classifier()

    assert first is mock_a
    assert second is mock_b


def test_returns_none_when_classifier_import_fails(tmp_path):
    fake_path = tmp_path / "model.joblib"
    fake_path.touch()

    with patch("app.services.ml.classifier.settings") as cfg:
        cfg.ml_model_path = str(fake_path)
        cfg.ml_unknown_threshold = 0.5
        with patch("ml.inference.Classifier", side_effect=Exception("corrupt model")):
            result = get_classifier()

    assert result is None
