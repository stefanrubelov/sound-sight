"""
Audio preprocessing pipeline for SoundSight.

Feature choice: MFCC (40 coefficients) over mel-spectrogram (128 bands).
Rationale: MFCCs produce compact 1-D feature vectors per clip, which work
well with sklearn classifiers (RandomForest/SVM) without a CNN. They also
encode perceptually relevant frequency information, matching how the human
auditory system processes sound. The resulting ~80-dim feature vector
(mean + std of 40 coefficients) is fast to compute and train on.
"""

import csv
import json
import logging
from pathlib import Path

import librosa
import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CLIP_DURATION = 1.0
HOP_DURATION = 0.5  # 50% overlap
N_MFCC = 40
SILENCE_THRESHOLD = 1e-4  # RMS below this → skip clip

TARGET_CLASSES = [
    "fire_alarm",
    "doorbell",
    "glass_breaking",
    "baby_crying",
    "dog_barking",
    "timer_beep",
    "water_running",
    "unknown",
]

CLASS_TO_IDX: dict[str, int] = {cls: i for i, cls in enumerate(TARGET_CLASSES)}
IDX_TO_CLASS: dict[int, str] = {i: cls for i, cls in enumerate(TARGET_CLASSES)}

# ESC-50 category name → our class label
ESC50_MAP: dict[str, str] = {
    "crackling_fire": "fire_alarm",
    "siren": "fire_alarm",
    "glass_breaking": "glass_breaking",
    "crying_baby": "baby_crying",
    "dog": "dog_barking",
    "water_drops": "water_running",
    "pouring_water": "water_running",
    "washing_machine": "water_running",
    "clock_alarm": "timer_beep",
    "clock_tick": "timer_beep",
    "door_wood_knock": "unknown",
    "church_bells": "unknown",
}

# UrbanSound8K class id → our class label (class_id 0-9 per the dataset)
US8K_MAP: dict[int, str] = {
    0: "unknown",  # air_conditioner
    1: "unknown",  # car_horn
    2: "unknown",  # children_playing
    3: "dog_barking",
    4: "unknown",  # drilling
    5: "unknown",  # engine_idling
    6: "unknown",  # gun_shot
    7: "unknown",  # jackhammer
    8: "fire_alarm",  # siren (closest to emergency alert)
    9: "unknown",  # street_music
}


_TARGET_RMS = 0.1  # normalize all clips to this RMS before feature extraction


def _normalize_rms(audio: np.ndarray) -> np.ndarray:
    rms = float(np.sqrt(np.mean(audio**2)))
    if rms < 1e-8:
        return audio
    return audio * (_TARGET_RMS / rms)


def extract_mfcc(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Return a 1-D feature vector: mean + std of each MFCC coefficient (2 * N_MFCC)."""
    audio = _normalize_rms(audio)
    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=N_MFCC)
    return np.concatenate([mfcc.mean(axis=1), mfcc.std(axis=1)])


def window_audio(audio: np.ndarray, sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Split audio into overlapping 1-second clips. Clips shorter than 1 s are zero-padded."""
    clip_len = int(CLIP_DURATION * sr)
    hop_len = int(HOP_DURATION * sr)
    clips = []
    start = 0
    while start < len(audio):
        clip = audio[start : start + clip_len]
        if len(clip) < clip_len:
            clip = np.pad(clip, (0, clip_len - len(clip)))
        clips.append(clip)
        start += hop_len
    return clips


def load_and_preprocess(path: str | Path) -> list[np.ndarray]:
    """Load an audio file and return MFCC feature vectors for each 1-second window."""
    audio, sr = librosa.load(str(path), sr=SAMPLE_RATE, mono=True)
    clips = window_audio(audio, sr)
    features = []
    for clip in clips:
        rms = float(np.sqrt(np.mean(clip**2)))
        if rms < SILENCE_THRESHOLD:
            continue
        features.append(extract_mfcc(clip, sr))
    return features


def pcm_bytes_to_audio(pcm_bytes: bytes, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Convert raw 16-bit signed PCM bytes to a float32 numpy array in [-1, 1]."""
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    return samples / 32768.0


# ---------------------------------------------------------------------------
# Dataset builders
# ---------------------------------------------------------------------------


def build_esc50_dataset(esc50_root: str | Path) -> tuple[list[np.ndarray], list[int]]:
    """Walk ESC-50 directory, filter to mapped classes, extract features."""
    esc50_root = Path(esc50_root)
    meta_path = esc50_root / "meta" / "esc50.csv"
    audio_dir = esc50_root / "audio"

    if not meta_path.exists():
        log.warning("ESC-50 metadata not found at %s — skipping", meta_path)
        return [], []

    X, y = [], []
    with open(meta_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row["category"]
            our_class = ESC50_MAP.get(category)
            if our_class is None:
                our_class = "unknown"
            label_idx = CLASS_TO_IDX[our_class]
            audio_path = audio_dir / row["filename"]
            if not audio_path.exists():
                continue
            try:
                feats = load_and_preprocess(audio_path)
                for feat in feats:
                    X.append(feat)
                    y.append(label_idx)
            except Exception as exc:
                log.warning("Failed to process %s: %s", audio_path, exc)
    return X, y


def build_us8k_dataset(us8k_root: str | Path) -> tuple[list[np.ndarray], list[int]]:
    """Walk UrbanSound8K directory, filter to mapped classes, extract features."""
    us8k_root = Path(us8k_root)
    meta_path = us8k_root / "metadata" / "UrbanSound8K.csv"
    audio_dir = us8k_root / "audio"

    if not meta_path.exists():
        log.warning("US8K metadata not found at %s — skipping", meta_path)
        return [], []

    X, y = [], []
    with open(meta_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            class_id = int(row["classID"])
            our_class = US8K_MAP.get(class_id, "unknown")
            label_idx = CLASS_TO_IDX[our_class]
            fold = row["fold"]
            filename = row["slice_file_name"]
            audio_path = audio_dir / f"fold{fold}" / filename
            if not audio_path.exists():
                continue
            try:
                feats = load_and_preprocess(audio_path)
                for feat in feats:
                    X.append(feat)
                    y.append(label_idx)
            except Exception as exc:
                log.warning("Failed to process %s: %s", audio_path, exc)
    return X, y


def build_custom_dataset(custom_root: str | Path) -> tuple[list[np.ndarray], list[int]]:
    """Load custom recordings. Expects subdirs named after target classes."""
    custom_root = Path(custom_root)
    X, y = [], []
    for class_name in TARGET_CLASSES:
        class_dir = custom_root / class_name
        if not class_dir.is_dir():
            continue
        label_idx = CLASS_TO_IDX[class_name]
        for audio_path in sorted(class_dir.glob("*.wav")) + sorted(class_dir.glob("*.mp3")):
            try:
                feats = load_and_preprocess(audio_path)
                for feat in feats:
                    X.append(feat)
                    y.append(label_idx)
            except Exception as exc:
                log.warning("Failed to process %s: %s", audio_path, exc)
    return X, y


def build_full_dataset(
    esc50_root: str | Path,
    us8k_root: str | Path,
    custom_root: str | Path,
) -> tuple[np.ndarray, np.ndarray]:
    """Combine all sources into X, y arrays."""
    X_all, y_all = [], []

    for X, y in [
        build_esc50_dataset(esc50_root),
        build_us8k_dataset(us8k_root),
        build_custom_dataset(custom_root),
    ]:
        X_all.extend(X)
        y_all.extend(y)

    return np.array(X_all, dtype=np.float32), np.array(y_all, dtype=np.int32)


def save_splits(
    X: np.ndarray,
    y: np.ndarray,
    output_dir: str | Path,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
) -> None:
    """Stratified train/val/test split, saved as .npz files."""
    from sklearn.model_selection import train_test_split

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    X_train, X_tmp, y_train, y_tmp = train_test_split(
        X, y, test_size=val_size + test_size, stratify=y, random_state=random_state
    )
    relative_test = test_size / (val_size + test_size)
    X_val, X_test, y_val, y_test = train_test_split(
        X_tmp, y_tmp, test_size=relative_test, stratify=y_tmp, random_state=random_state
    )

    np.savez(output_dir / "train.npz", X=X_train, y=y_train)
    np.savez(output_dir / "val.npz", X=X_val, y=y_val)
    np.savez(output_dir / "test.npz", X=X_test, y=y_test)

    log.info(
        "Saved splits — train: %d, val: %d, test: %d",
        len(y_train),
        len(y_val),
        len(y_test),
    )

    meta = {
        "classes": TARGET_CLASSES,
        "class_to_idx": CLASS_TO_IDX,
        "n_mfcc": N_MFCC,
        "sample_rate": SAMPLE_RATE,
        "clip_duration": CLIP_DURATION,
        "hop_duration": HOP_DURATION,
        "train_size": int(len(y_train)),
        "val_size": int(len(y_val)),
        "test_size": int(len(y_test)),
    }
    with open(output_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Build SoundSight dataset splits")
    parser.add_argument("--esc50", default="ml/data/esc50")
    parser.add_argument("--us8k", default="ml/data/us8k")
    parser.add_argument("--custom", default="ml/data/custom")
    parser.add_argument("--out", default="ml/data/processed")
    args = parser.parse_args()

    X, y = build_full_dataset(args.esc50, args.us8k, args.custom)
    if len(X) == 0:
        print("No data found — place ESC-50/US8K in ml/data/ or add custom clips.")
    else:
        print(f"Total samples: {len(X)}")
        save_splits(X, y, args.out)
        print(f"Splits saved to {args.out}/")
