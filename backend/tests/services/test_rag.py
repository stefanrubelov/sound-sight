"""Tests for RAG (Retrieval-Augmented Generation) services.

Uses a temporary in-memory ChromaDB client so tests don't touch the persistent
rag/chroma_data directory or require sentence-transformers to be downloaded.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_embeddings():
    """Return a mock Embeddings object that returns fixed-length vectors."""
    emb = MagicMock()
    emb.embed_documents.side_effect = lambda texts: [[0.1] * 384 for _ in texts]
    emb.embed_query.return_value = [0.1] * 384
    return emb


def _make_in_memory_chroma(name: str, mock_embeddings):
    """Create a real Chroma instance backed by an in-memory (ephemeral) ChromaDB client."""
    import chromadb
    from langchain_chroma import Chroma

    client = chromadb.EphemeralClient()
    return Chroma(
        client=client,
        collection_name=name,
        embedding_function=mock_embeddings,
    )


# ---------------------------------------------------------------------------
# chroma_client
# ---------------------------------------------------------------------------


class TestUpsertTexts:
    def test_upsert_new_documents(self, tmp_path):
        """upsert_texts adds documents when they don't exist yet."""
        mock_emb = _make_mock_embeddings()
        col = _make_in_memory_chroma("test_new", mock_emb)

        from app.services.rag.chroma_client import upsert_texts

        upsert_texts(col, texts=["hello"], metadatas=[{"k": "v"}], ids=["id1"])
        result = col.get(ids=["id1"])
        assert result["documents"] == ["hello"]

    def test_upsert_overwrites_existing(self, tmp_path):
        """upsert_texts replaces a document that already exists under the same id."""
        mock_emb = _make_mock_embeddings()
        col = _make_in_memory_chroma("test_overwrite", mock_emb)

        from app.services.rag.chroma_client import upsert_texts

        upsert_texts(col, texts=["original"], metadatas=[{}], ids=["id1"])
        upsert_texts(col, texts=["updated"], metadatas=[{}], ids=["id1"])

        result = col.get(ids=["id1"])
        assert result["documents"] == ["updated"]


# ---------------------------------------------------------------------------
# event_history
# ---------------------------------------------------------------------------


class TestEventHistory:
    def _patched_collection(self, col):
        return patch("app.services.rag.event_history.get_collection", return_value=col)

    def test_embed_event_stores_document(self):
        mock_emb = _make_mock_embeddings()
        col = _make_in_memory_chroma("event_history", mock_emb)

        with self._patched_collection(col):
            from app.services.rag.event_history import embed_event

            embed_event(
                event_id=42,
                class_name="doorbell",
                timestamp="2024-01-01T12:00:00",
                device_id=1,
                duration=2.5,
                confidence=0.91,
                room="hallway",
                summary="The doorbell rang.",
            )

        result = col.get(ids=["event-42"])
        assert len(result["documents"]) == 1
        assert "doorbell" in result["documents"][0]

    def test_embed_event_gracefully_handles_failure(self):
        """embed_event must not raise even when the collection is unavailable."""
        with patch(
            "app.services.rag.event_history.get_collection",
            side_effect=RuntimeError("chroma down"),
        ):
            from app.services.rag.event_history import embed_event

            # Should not raise
            embed_event(
                event_id=1,
                class_name="fire_alarm",
                timestamp="2024-01-01T00:00:00",
                device_id=None,
                duration=1.0,
                confidence=0.5,
            )

    def test_retrieve_similar_events_returns_list(self):
        mock_emb = _make_mock_embeddings()
        col = _make_in_memory_chroma("event_history_r", mock_emb)

        with patch("app.services.rag.event_history.get_collection", return_value=col):
            from app.services.rag.event_history import embed_event, retrieve_similar_events

            embed_event(
                event_id=10,
                class_name="baby_crying",
                timestamp="2024-01-01T08:00:00",
                device_id=2,
                duration=15.0,
                confidence=0.88,
                room="bedroom",
                summary="Baby crying in the bedroom.",
            )
            results = retrieve_similar_events("baby crying bedroom", k=3)

        assert isinstance(results, list)
        assert len(results) >= 1
        assert "text" in results[0]
        assert "metadata" in results[0]

    def test_retrieve_similar_events_graceful_on_failure(self):
        with patch(
            "app.services.rag.event_history.get_collection",
            side_effect=RuntimeError("unavailable"),
        ):
            from app.services.rag.event_history import retrieve_similar_events

            result = retrieve_similar_events("anything")
            assert result == []


# ---------------------------------------------------------------------------
# home_knowledge
# ---------------------------------------------------------------------------


class TestHomeKnowledge:
    def _patched_collection(self, col):
        return patch("app.services.rag.home_knowledge.get_collection", return_value=col)

    def test_index_profile_stores_description(self):
        mock_emb = _make_mock_embeddings()
        col = _make_in_memory_chroma("home_knowledge", mock_emb)

        with self._patched_collection(col):
            from app.services.rag.home_knowledge import index_profile

            index_profile(
                profile_id=1,
                home_description="I live alone in a flat with a dog.",
                notes=None,
            )

        result = col.get(ids=["profile-1-description"])
        assert result["documents"][0] == "I live alone in a flat with a dog."

    def test_index_profile_stores_notes(self):
        mock_emb = _make_mock_embeddings()
        col = _make_in_memory_chroma("home_knowledge_n", mock_emb)

        with self._patched_collection(col):
            from app.services.rag.home_knowledge import index_profile

            index_profile(profile_id=2, home_description=None, notes="Extra quiet at night.")

        result = col.get(ids=["profile-2-notes"])
        assert "quiet at night" in result["documents"][0]

    def test_index_profile_empty_is_noop(self):
        mock_emb = _make_mock_embeddings()
        col = _make_in_memory_chroma("home_knowledge_e", mock_emb)

        with self._patched_collection(col):
            from app.services.rag.home_knowledge import index_profile

            index_profile(profile_id=3, home_description=None, notes=None)
            assert col.get()["documents"] == []

    def test_retrieve_home_context_returns_string(self):
        mock_emb = _make_mock_embeddings()
        col = _make_in_memory_chroma("home_knowledge_ret", mock_emb)

        with self._patched_collection(col):
            from app.services.rag.home_knowledge import index_profile, retrieve_home_context

            index_profile(
                profile_id=4, home_description="Family home with small children.", notes=None
            )
            ctx = retrieve_home_context("baby crying", k=2)

        assert isinstance(ctx, str)
        assert len(ctx) > 0

    def test_retrieve_home_context_graceful_on_failure(self):
        with patch(
            "app.services.rag.home_knowledge.get_collection",
            side_effect=RuntimeError("down"),
        ):
            from app.services.rag.home_knowledge import retrieve_home_context

            assert retrieve_home_context("query") == ""


# ---------------------------------------------------------------------------
# sound_class_kb
# ---------------------------------------------------------------------------


class TestSoundClassKB:
    @pytest.fixture
    def corpus_dir(self, tmp_path: Path) -> Path:
        """Create a small temporary corpus with two Markdown files."""
        d = tmp_path / "sound_classes"
        d.mkdir()
        (d / "fire_alarm.md").write_text("# Fire Alarm\nAlways evacuate.")
        (d / "doorbell.md").write_text("# Doorbell\nSomeone is at the door.")
        return d

    def _patched_collection(self, col):
        return patch("app.services.rag.sound_class_kb.get_collection", return_value=col)

    def test_index_sound_classes_returns_count(self, corpus_dir):
        mock_emb = _make_mock_embeddings()
        col = _make_in_memory_chroma("sound_class_kb_idx", mock_emb)

        with self._patched_collection(col):
            from app.services.rag.sound_class_kb import index_sound_classes

            n = index_sound_classes(corpus_dir)

        assert n == 2

    def test_index_sound_classes_empty_corpus(self, tmp_path):
        mock_emb = _make_mock_embeddings()
        col = _make_in_memory_chroma("sound_class_kb_empty", mock_emb)
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with self._patched_collection(col):
            from app.services.rag.sound_class_kb import index_sound_classes

            n = index_sound_classes(empty_dir)

        assert n == 0

    def test_retrieve_class_info_exact_match(self, corpus_dir):
        mock_emb = _make_mock_embeddings()
        col = _make_in_memory_chroma("sound_class_kb_exact", mock_emb)

        with self._patched_collection(col):
            from app.services.rag.sound_class_kb import index_sound_classes, retrieve_class_info

            index_sound_classes(corpus_dir)
            info = retrieve_class_info("fire_alarm")

        assert "evacuate" in info.lower()

    def test_retrieve_class_info_graceful_on_failure(self):
        with patch(
            "app.services.rag.sound_class_kb.get_collection",
            side_effect=RuntimeError("down"),
        ):
            from app.services.rag.sound_class_kb import retrieve_class_info

            assert retrieve_class_info("fire_alarm") == ""
