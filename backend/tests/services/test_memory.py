"""Tests for Phase 9 memory services — session memory and baselines."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Event


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _make_event(class_name: str, duration: float, confidence: float, hour: int = 10) -> Event:
    # Use a recent timestamp so events fall within the 30-day baseline window
    from datetime import date

    today = date.today()
    ts = datetime(today.year, today.month, today.day, hour, 0, 0, tzinfo=timezone.utc)
    return Event(
        device_id=1,
        class_name=class_name,
        confidence=confidence,
        duration=duration,
        timestamp=ts,
    )


# ---------------------------------------------------------------------------
# Session memory
# ---------------------------------------------------------------------------


class TestSessionMemory:
    def setup_method(self):
        # Each test gets a clean store
        from app.services.memory import session as sess_mod

        sess_mod._store.clear()

    def test_get_session_memory_creates_new(self):
        from app.services.memory.session import active_session_count, get_session_memory

        mem = get_session_memory("abc")
        assert mem is not None
        assert active_session_count() == 1

    def test_same_id_returns_same_history(self):
        from app.services.memory.session import add_user_message, get_messages, get_session_memory

        get_session_memory("s1")
        add_user_message("s1", "hello")
        msgs = get_messages("s1")
        assert len(msgs) == 1
        assert msgs[0].content == "hello"

    def test_different_ids_are_isolated(self):
        from app.services.memory.session import add_user_message, get_messages

        add_user_message("session-a", "message for A")
        add_user_message("session-b", "message for B")

        assert len(get_messages("session-a")) == 1
        assert len(get_messages("session-b")) == 1
        assert get_messages("session-a")[0].content == "message for A"

    def test_clear_session_removes_entry(self):
        from app.services.memory.session import (
            active_session_count,
            add_user_message,
            clear_session,
        )

        add_user_message("to-clear", "hi")
        assert active_session_count() == 1
        clear_session("to-clear")
        assert active_session_count() == 0

    def test_clear_nonexistent_session_is_noop(self):
        from app.services.memory.session import clear_session

        clear_session("does-not-exist")  # must not raise

    def test_purge_expired_removes_old_sessions(self):
        from datetime import timedelta

        from app.services.memory import session as sess_mod
        from app.services.memory.session import (
            active_session_count,
            get_session_memory,
            purge_expired,
        )

        get_session_memory("fresh")
        get_session_memory("stale")

        # Manually backdate the stale session
        sess_mod._store["stale"].last_used -= timedelta(minutes=60)

        removed = purge_expired(ttl_minutes=30)
        assert removed == 1
        assert active_session_count() == 1

    def test_purge_does_not_remove_fresh_sessions(self):
        from app.services.memory.session import (
            active_session_count,
            get_session_memory,
            purge_expired,
        )

        get_session_memory("s1")
        get_session_memory("s2")
        removed = purge_expired(ttl_minutes=30)
        assert removed == 0
        assert active_session_count() == 2

    def test_window_trims_old_messages(self):
        from app.services.memory.session import (
            WINDOW_SIZE,
            add_ai_message,
            add_user_message,
            get_messages,
        )

        sid = "windowed"
        # Add more than WINDOW_SIZE * 2 messages
        for i in range(WINDOW_SIZE * 2 + 4):
            add_user_message(sid, f"user {i}")
            add_ai_message(sid, f"ai {i}")

        # Trigger the window trim by calling get_session_memory again
        from app.services.memory.session import get_session_memory

        get_session_memory(sid)
        msgs = get_messages(sid)
        assert len(msgs) <= WINDOW_SIZE * 2


# ---------------------------------------------------------------------------
# Baseline computation
# ---------------------------------------------------------------------------


class TestBaselineComputation:
    @pytest.mark.anyio
    async def test_compute_baselines_empty_db(self, db_session):
        from app.services.memory.baseline import compute_baselines

        result = await compute_baselines(db_session)
        assert result == {}

    @pytest.mark.anyio
    async def test_compute_baselines_basic_stats(self, db_session):
        from app.services.memory.baseline import compute_baselines

        events = [
            _make_event("doorbell", duration=2.0, confidence=0.9, hour=10),
            _make_event("doorbell", duration=3.0, confidence=0.85, hour=14),
            _make_event("doorbell", duration=2.5, confidence=0.92, hour=23),  # night
        ]
        for e in events:
            db_session.add(e)
        await db_session.commit()

        result = await compute_baselines(db_session)
        assert "doorbell" in result
        stats = result["doorbell"]
        assert stats["total_events"] == 3
        assert stats["mean_duration"] == pytest.approx(2.5, rel=0.01)
        assert stats["night_ratio"] == pytest.approx(1 / 3, rel=0.01)

    @pytest.mark.anyio
    async def test_compute_baselines_excludes_unknown(self, db_session):
        from app.services.memory.baseline import compute_baselines

        db_session.add(_make_event("unknown", duration=1.0, confidence=0.3))
        db_session.add(_make_event("fire_alarm", duration=5.0, confidence=0.95))
        await db_session.commit()

        result = await compute_baselines(db_session)
        assert "unknown" not in result
        assert "fire_alarm" in result

    @pytest.mark.anyio
    async def test_compute_baselines_multiple_classes(self, db_session):
        from app.services.memory.baseline import compute_baselines

        for cls in ["doorbell", "fire_alarm", "dog_barking"]:
            db_session.add(_make_event(cls, duration=2.0, confidence=0.88))
        await db_session.commit()

        result = await compute_baselines(db_session)
        assert len(result) == 3

    @pytest.mark.anyio
    async def test_save_baselines_creates_records(self, db_session):
        from sqlalchemy import select

        from app.db.models import Baseline
        from app.services.memory.baseline import save_baselines

        baselines = {
            "doorbell": {
                "total_events": 10,
                "count_per_day": 0.333,
                "mean_duration": 2.0,
                "std_duration": 0.5,
                "mean_confidence": 0.9,
                "night_ratio": 0.1,
            }
        }
        await save_baselines(db_session, baselines)

        result = await db_session.execute(select(Baseline).where(Baseline.class_name == "doorbell"))
        baseline = result.scalar_one()
        import json

        stats = json.loads(baseline.stats_json)
        assert stats["total_events"] == 10

    @pytest.mark.anyio
    async def test_save_baselines_upserts(self, db_session):
        from sqlalchemy import select

        from app.db.models import Baseline
        from app.services.memory.baseline import save_baselines

        initial = {
            "doorbell": {
                "total_events": 5,
                "count_per_day": 0.16,
                "mean_duration": 2.0,
                "std_duration": 0.0,
                "mean_confidence": 0.9,
                "night_ratio": 0.0,
            }
        }
        updated = {
            "doorbell": {
                "total_events": 10,
                "count_per_day": 0.33,
                "mean_duration": 2.5,
                "std_duration": 0.5,
                "mean_confidence": 0.88,
                "night_ratio": 0.1,
            }
        }

        await save_baselines(db_session, initial)
        await save_baselines(db_session, updated)

        result = await db_session.execute(select(Baseline))
        baselines = result.scalars().all()
        assert len(baselines) == 1  # no duplicate rows

        import json

        assert json.loads(baselines[0].stats_json)["total_events"] == 10

    def test_embed_baselines_is_resilient(self):
        """embed_baselines must not raise even when ChromaDB is unavailable."""
        from app.services.memory.baseline import embed_baselines

        with patch(
            "app.services.rag.chroma_client.get_collection",
            side_effect=RuntimeError("chroma down"),
        ):
            embed_baselines(
                {
                    "fire_alarm": {
                        "total_events": 5,
                        "count_per_day": 0.1,
                        "mean_duration": 3.0,
                        "std_duration": 0.0,
                        "mean_confidence": 0.9,
                        "night_ratio": 0.2,
                    }
                }
            )
