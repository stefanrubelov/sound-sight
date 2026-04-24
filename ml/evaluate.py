"""
Evaluation script — generates confusion matrix, per-class metrics, and
confidence distribution plots. Run after train.py.
"""

import json
import logging
from pathlib import Path

import joblib
import numpy as np

log = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
DATA_DIR = Path(__file__).parent / "data" / "processed"


def evaluate(
    data_dir: Path = DATA_DIR,
    artifacts_dir: Path = ARTIFACTS_DIR,
) -> dict:
    """Load the trained model, run on test split, produce plots and REPORT.md."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.metrics import (
            ConfusionMatrixDisplay,
            accuracy_score,
            classification_report,
            confusion_matrix,
        )
    except ImportError as e:
        log.error("Missing dependency: %s — install matplotlib and scikit-learn", e)
        raise

    model_path = artifacts_dir / "soundsight_classifier.joblib"
    clf = joblib.load(model_path)
    log.info("Loaded model from %s", model_path)

    with open(data_dir / "meta.json") as f:
        meta = json.load(f)
    classes = meta["classes"]

    data = np.load(data_dir / "test.npz")
    X_test, y_test = data["X"], data["y"]
    log.info("Test samples: %d", len(y_test))

    y_pred = clf.predict(X_test)
    proba = clf.predict_proba(X_test)
    top_confidences = proba.max(axis=1)

    acc = accuracy_score(y_test, y_pred)
    report_str = classification_report(y_test, y_pred, target_names=classes)
    report_dict = classification_report(
        y_test, y_pred, target_names=classes, output_dict=True
    )
    log.info("Test accuracy: %.4f\n%s", acc, report_str)

    # --- Confusion matrix ---
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(10, 8))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=classes)
    disp.plot(ax=ax, xticks_rotation=45, colorbar=False)
    ax.set_title(f"SoundSight Confusion Matrix (Test accuracy: {acc:.3f})")
    plt.tight_layout()
    cm_path = artifacts_dir / "confusion_matrix.png"
    fig.savefig(cm_path, dpi=150)
    plt.close(fig)
    log.info("Confusion matrix saved to %s", cm_path)

    # --- Confidence distribution ---
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(top_confidences, bins=30, edgecolor="black")
    ax.set_xlabel("Confidence (max class probability)")
    ax.set_ylabel("Count")
    ax.set_title("Prediction confidence distribution")
    ax.axvline(x=0.5, color="red", linestyle="--", label="50% threshold")
    ax.legend()
    plt.tight_layout()
    conf_path = artifacts_dir / "confidence_distribution.png"
    fig.savefig(conf_path, dpi=150)
    plt.close(fig)
    log.info("Confidence distribution saved to %s", conf_path)

    # --- Per-class confidence box plot ---
    fig, ax = plt.subplots(figsize=(10, 5))
    per_class_conf = [top_confidences[y_test == i] for i in range(len(classes))]
    ax.boxplot(per_class_conf, labels=classes, vert=True)
    plt.xticks(rotation=45, ha="right")
    ax.set_ylabel("Top confidence")
    ax.set_title("Per-class confidence distribution")
    plt.tight_layout()
    box_path = artifacts_dir / "per_class_confidence.png"
    fig.savefig(box_path, dpi=150)
    plt.close(fig)

    results = {
        "test_accuracy": float(acc),
        "classification_report": report_dict,
        "confidence_p5": float(np.percentile(top_confidences, 5)),
        "confidence_p50": float(np.percentile(top_confidences, 50)),
        "confidence_p95": float(np.percentile(top_confidences, 95)),
    }
    with open(artifacts_dir / "eval_metrics.json", "w") as f:
        json.dump(results, f, indent=2)

    _write_report(acc, report_str, report_dict, classes, results, artifacts_dir)
    return results


def _write_report(acc, report_str, report_dict, classes, results, artifacts_dir):
    lines = [
        "# SoundSight ML Evaluation Report\n",
        "## Model\n",
        "- **Architecture:** RandomForestClassifier (scikit-learn)\n",
        "- **Features:** MFCC — 40 coefficients, mean + std → 80-dim vector per 1-second clip\n",
        "- **Sample rate:** 16 kHz, mono\n",
        "- **Window:** 1 s clips with 50% overlap\n",
        "- **Feature choice rationale:** MFCCs yield compact, perceptually motivated vectors that\n",
        "  pair well with tree-based ensembles without requiring a GPU or a CNN training loop.\n",
        "  RandomForest with `class_weight='balanced'` handles the skewed class distribution from\n",
        "  ESC-50 + UrbanSound8K without oversampling.\n\n",
        "## Dataset\n",
        "- ESC-50 (mapped subset)\n",
        "- UrbanSound8K (mapped subset)\n",
        "- Custom recordings per target class\n\n",
        "## Target Classes\n",
    ]
    for cls in classes:
        lines.append(f"- `{cls}`\n")

    lines += [
        "\n## Results\n",
        f"**Test accuracy: {acc:.4f}**\n\n",
        "```\n",
        report_str,
        "```\n\n",
        "## Plots\n",
        "- `artifacts/confusion_matrix.png` — per-class confusion matrix\n",
        "- `artifacts/confidence_distribution.png` — histogram of max-class probability\n",
        "- `artifacts/per_class_confidence.png` — box plot of confidence per class\n\n",
        "## Unknown Threshold\n",
        f"P5 confidence: {results['confidence_p5']:.3f}  \n",
        f"P50 confidence: {results['confidence_p50']:.3f}  \n",
        f"P95 confidence: {results['confidence_p95']:.3f}  \n\n",
        "Clips where the top class probability is below **0.50** are returned as `unknown`.\n",
        "This threshold can be adjusted in `ml/inference.py`.\n",
    ]

    report_path = Path(__file__).parent / "REPORT.md"
    with open(report_path, "w") as f:
        f.writelines(lines)
    log.info("REPORT.md written to %s", report_path)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Evaluate SoundSight classifier")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--artifacts-dir", default=str(ARTIFACTS_DIR))
    args = parser.parse_args()

    results = evaluate(Path(args.data_dir), Path(args.artifacts_dir))
    print(f"\nTest accuracy: {results['test_accuracy']:.4f}")
