"""Short-term session memory for interactive rule-creation flows.

Each browser session gets an isolated ConversationWindow keyed by a UUID the
frontend generates.  Entries expire after SESSION_TTL_MINUTES of inactivity so
the store never grows unbounded.

Usage::

    mem = get_session_memory(session_id)
    mem.add_user_message("Vibrate if glass breaks after 22:00")
    mem.add_ai_message("Rule created: glass_breaking after 22:00, vibration alert.")
    history = mem.messages          # list[BaseMessage]
    clear_session(session_id)       # explicit clear on logout / tab close
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage

log = logging.getLogger(__name__)

SESSION_TTL_MINUTES = 30
WINDOW_SIZE = 10  # keep last N human+AI turns (20 messages)


@dataclass
class _Entry:
    history: InMemoryChatMessageHistory = field(default_factory=InMemoryChatMessageHistory)
    last_used: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.last_used = datetime.now(timezone.utc)

    def is_expired(self, ttl_minutes: int = SESSION_TTL_MINUTES) -> bool:
        return datetime.now(timezone.utc) - self.last_used > timedelta(minutes=ttl_minutes)


# Module-level store — safe for single-process FastAPI (Uvicorn default)
_store: dict[str, _Entry] = {}


def get_session_memory(session_id: str) -> InMemoryChatMessageHistory:
    """Return the chat history for *session_id*, creating it if new."""
    if session_id not in _store:
        _store[session_id] = _Entry()
        log.debug("Created session memory: %s", session_id)
    entry = _store[session_id]
    entry.touch()
    # Enforce window: trim to last WINDOW_SIZE * 2 messages
    msgs = entry.history.messages
    if len(msgs) > WINDOW_SIZE * 2:
        entry.history.clear()
        for msg in msgs[-(WINDOW_SIZE * 2) :]:
            entry.history.add_message(msg)
    return entry.history


def add_user_message(session_id: str, text: str) -> None:
    get_session_memory(session_id).add_user_message(text)


def add_ai_message(session_id: str, text: str) -> None:
    get_session_memory(session_id).add_ai_message(text)


def get_messages(session_id: str) -> list[BaseMessage]:
    return get_session_memory(session_id).messages


def clear_session(session_id: str) -> None:
    """Explicitly clear and remove a session."""
    if session_id in _store:
        del _store[session_id]
        log.debug("Cleared session memory: %s", session_id)


def purge_expired(ttl_minutes: int = SESSION_TTL_MINUTES) -> int:
    """Remove all expired sessions. Returns the number purged."""
    expired = [sid for sid, e in _store.items() if e.is_expired(ttl_minutes)]
    for sid in expired:
        del _store[sid]
    if expired:
        log.info("Purged %d expired session(s)", len(expired))
    return len(expired)


def active_session_count() -> int:
    return len(_store)
