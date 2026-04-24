"""Unit tests for ml/preprocess.py — shape, dtype, and silence handling."""

import numpy as np

from ml.preprocess import (
    N_MFCC,
    SAMPLE_RATE,
    extract_mfcc,
    load_and_preprocess,
    pcm_bytes_to_audio,
    window_audio,
)


# ---------------------------------------------------------------------------
# extract_mfcc
# ---------------------------------------------------------------------------


class TestExtractMfcc:
    def test_output_shape(self):
        audio = np.random.randn(SAMPLE_RATE).astype(np.float32)
        feat = extract_mfcc(audio)
        assert feat.shape == (
            2 * N_MFCC,
        ), f"Expected ({2 * N_MFCC},), got {feat.shape}"

    def test_output_dtype(self):
        audio = np.random.randn(SAMPLE_RATE).astype(np.float32)
        feat = extract_mfcc(audio)
        assert feat.dtype in (np.float32, np.float64)

    def test_deterministic(self):
        np.random.seed(0)
        audio = np.random.randn(SAMPLE_RATE).astype(np.float32)
        f1 = extract_mfcc(audio)
        f2 = extract_mfcc(audio)
        np.testing.assert_array_equal(f1, f2)

    def test_silence_returns_finite(self):
        audio = np.zeros(SAMPLE_RATE, dtype=np.float32)
        feat = extract_mfcc(audio)
        assert np.all(np.isfinite(feat))


# ---------------------------------------------------------------------------
# window_audio
# ---------------------------------------------------------------------------


class TestWindowAudio:
    def test_single_clip_short(self):
        """Audio shorter than 1 s → exactly one zero-padded clip."""
        audio = np.ones(SAMPLE_RATE // 2, dtype=np.float32)
        clips = window_audio(audio)
        assert len(clips) == 1
        assert len(clips[0]) == SAMPLE_RATE

    def test_exact_one_second(self):
        audio = np.ones(SAMPLE_RATE, dtype=np.float32)
        clips = window_audio(audio)
        assert len(clips) >= 1
        for clip in clips:
            assert len(clip) == SAMPLE_RATE

    def test_overlap_produces_multiple_clips(self):
        audio = np.ones(SAMPLE_RATE * 3, dtype=np.float32)
        clips = window_audio(audio)
        assert len(clips) > 1

    def test_all_clips_same_length(self):
        audio = np.random.randn(int(SAMPLE_RATE * 2.7)).astype(np.float32)
        clips = window_audio(audio)
        for clip in clips:
            assert len(clip) == SAMPLE_RATE


# ---------------------------------------------------------------------------
# pcm_bytes_to_audio
# ---------------------------------------------------------------------------


class TestPcmBytesToAudio:
    def test_converts_int16_to_float(self):
        samples = np.array([0, 16384, -16384, 32767], dtype=np.int16)
        audio = pcm_bytes_to_audio(samples.tobytes())
        assert audio.dtype == np.float32
        assert np.max(np.abs(audio)) <= 1.0

    def test_zero_bytes(self):
        samples = np.zeros(100, dtype=np.int16)
        audio = pcm_bytes_to_audio(samples.tobytes())
        np.testing.assert_array_equal(audio, np.zeros(100, dtype=np.float32))

    def test_max_value_clamps_to_one(self):
        samples = np.array([32767], dtype=np.int16)
        audio = pcm_bytes_to_audio(samples.tobytes())
        assert abs(audio[0] - 32767 / 32768.0) < 1e-5

    def test_length_preserved(self):
        n = 4000
        samples = np.random.randint(-32768, 32767, n, dtype=np.int16)
        audio = pcm_bytes_to_audio(samples.tobytes())
        assert len(audio) == n


# ---------------------------------------------------------------------------
# load_and_preprocess (silence filtering)
# ---------------------------------------------------------------------------


class TestLoadAndPreprocess:
    def test_silent_file_returns_empty(self, tmp_path):
        """A file containing only silence should yield no feature vectors."""
        import soundfile as sf

        path = tmp_path / "silence.wav"
        silent = np.zeros(SAMPLE_RATE * 2, dtype=np.float32)
        sf.write(str(path), silent, SAMPLE_RATE)
        feats = load_and_preprocess(path)
        assert feats == [], f"Expected [], got {len(feats)} clips"

    def test_noisy_file_returns_features(self, tmp_path):
        import soundfile as sf

        path = tmp_path / "noise.wav"
        noise = np.random.randn(SAMPLE_RATE * 2).astype(np.float32) * 0.5
        sf.write(str(path), noise, SAMPLE_RATE)
        feats = load_and_preprocess(path)
        assert len(feats) > 0
        for feat in feats:
            assert feat.shape == (2 * N_MFCC,)
