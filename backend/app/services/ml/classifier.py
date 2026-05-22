"""
Thin wrapper around ml.inference.Classifier for use inside the FastAPI process.

Lazily loads the model on first use so startup isn't blocked when the artifact
doesn't exist yet (e.g. in CI or before training has been run).
"""

import logging
from pathlib import Path

from app.config import settings

log = logging.getLogger(__name__)

_classifier = None


def get_classifier():
    """Return the module-level Classifier singleton, loading it on first call."""
    global _classifier
    if _classifier is not None:
        return _classifier

    model_path = Path(settings.ml_model_path)
    if not model_path.exists():
        log.warning(
            "Model artifact not found at %s — classifier unavailable. "
            "Run ml/train.py to generate the artifact.",
            model_path,
        )
        return None

    try:
        import sys
        from pathlib import Path as _Path

        _repo_root = str(_Path(__file__).parent.parent.parent.parent.parent)
        if _repo_root not in sys.path:
            sys.path.insert(0, _repo_root)

        from ml.inference import Classifier

        _classifier = Classifier(
            model_path=model_path,
            threshold=settings.ml_unknown_threshold,
        )
        log.info("Classifier loaded from %s", model_path)
    except Exception as exc:
        log.error("Failed to load classifier: %s", exc)
        return None

    return _classifier


def reset_classifier() -> None:
    """Force the next call to get_classifier() to reload from disk (used in tests)."""
    global _classifier
    _classifier = None
