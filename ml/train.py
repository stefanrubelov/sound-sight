"""
Training script for SoundSight audio classifier.

Model: RandomForestClassifier (sklearn) on MFCC features.
Chosen over CNN+spectrograms for speed and simplicity; delivers sufficient
accuracy for 6–8 household sound classes on MFCC features.
"""

import json
import logging
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

log = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
DATA_DIR = Path(__file__).parent / "data" / "processed"
MODEL_PATH = ARTIFACTS_DIR / "soundsight_classifier.joblib"

# Cap unknown samples at this multiple of the largest non-unknown class.
# Keeps the dataset balanced without throwing away all unknown data.
UNKNOWN_OVERSAMPLE_RATIO = 2


def load_split(split: str, data_dir: Path = DATA_DIR) -> tuple[np.ndarray, np.ndarray]:
    path = data_dir / f"{split}.npz"
    data = np.load(path)
    return data["X"], data["y"]


def _balance_unknown(
    X: np.ndarray, y: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Downsample the unknown class so it is at most UNKNOWN_OVERSAMPLE_RATIO × the largest non-unknown class."""
    unique, counts = np.unique(y, return_counts=True)
    unknown_idx = int(y.max())  # unknown is always the last class index
    non_unknown_counts = [c for cls, c in zip(unique, counts) if cls != unknown_idx]
    if not non_unknown_counts:
        return X, y
    max_non_unknown = max(non_unknown_counts)
    cap = max_non_unknown * UNKNOWN_OVERSAMPLE_RATIO

    unknown_mask = y == unknown_idx
    n_unknown = unknown_mask.sum()
    if n_unknown <= cap:
        return X, y

    # Randomly select `cap` unknown samples
    unknown_positions = np.where(unknown_mask)[0]
    keep = rng.choice(unknown_positions, size=cap, replace=False)
    other_positions = np.where(~unknown_mask)[0]
    selected = np.sort(np.concatenate([other_positions, keep]))
    return X[selected], y[selected]


def train(
    data_dir: Path = DATA_DIR,
    artifacts_dir: Path = ARTIFACTS_DIR,
    n_estimators: int = 500,
    max_depth: int | None = None,
    random_state: int = 42,
) -> dict:
    """Train the classifier and return validation metrics."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    log.info("Loading training data from %s", data_dir)
    X_train, y_train = load_split("train", data_dir)
    X_val, y_val = load_split("val", data_dir)

    with open(data_dir / "meta.json") as f:
        meta = json.load(f)
    classes = meta["classes"]

    rng = np.random.default_rng(random_state)
    X_train, y_train = _balance_unknown(X_train, y_train, rng)

    unique, counts = np.unique(y_train, return_counts=True)
    log.info("Balanced training set — %d samples:", len(y_train))
    for cls_idx, cnt in zip(unique, counts):
        log.info("  %s: %d", classes[cls_idx], cnt)

    log.info("Feature dimension: %d  |  Classes: %s", X_train.shape[1], classes)

    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        class_weight="balanced",
        n_jobs=-1,
        random_state=random_state,
    )

    t0 = time.time()
    clf.fit(X_train, y_train)
    train_time = time.time() - t0
    log.info("Training done in %.1fs", train_time)

    val_preds = clf.predict(X_val)
    val_acc = accuracy_score(y_val, val_preds)
    present_labels = sorted(set(y_val) | set(val_preds))
    present_names = [classes[i] for i in present_labels]
    report = classification_report(
        y_val, val_preds, labels=present_labels, target_names=present_names, output_dict=True
    )

    log.info("Validation accuracy: %.4f", val_acc)
    log.info(
        "\n%s",
        classification_report(y_val, val_preds, labels=present_labels, target_names=present_names),
    )

    model_path = artifacts_dir / "soundsight_classifier.joblib"
    joblib.dump(clf, model_path)
    log.info("Model saved to %s", model_path)

    metrics = {
        "val_accuracy": float(val_acc),
        "train_time_s": round(train_time, 2),
        "n_estimators": n_estimators,
        "max_depth": max_depth,
        "classes": classes,
        "classification_report": report,
    }
    with open(artifacts_dir / "train_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Train SoundSight classifier")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--artifacts-dir", default=str(ARTIFACTS_DIR))
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--max-depth", type=int, default=None)
    args = parser.parse_args()

    metrics = train(
        data_dir=Path(args.data_dir),
        artifacts_dir=Path(args.artifacts_dir),
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
    )
    print(f"\nValidation accuracy: {metrics['val_accuracy']:.4f}")
