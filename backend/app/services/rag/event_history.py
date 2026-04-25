"""Collection 1 — Event History.

Each detected sound event is embedded as a short natural-language document.
The collection is used by the report generator and anomaly narrator to surface
semantically related past events.
"""

from __future__ import annotations

import logging

from app.services.rag.chroma_client import get_collection, upsert_texts

log = logging.getLogger(__name__)

_COLLECTION = "event_history"


def _event_text(class_name: str, room: str, duration: float, summary: str | None) -> str:
    label = class_name.replace("_", " ")
    base = f"{label} detected in {room} for {duration:.1f} seconds"
    return f"{base}. {summary}" if summary else base


def embed_event(
    event_id: int,
    class_name: str,
    timestamp: str,
    device_id: int | None,
    duration: float,
    confidence: float,
    room: str = "unknown",
    summary: str | None = None,
) -> None:
    """Upsert a single event into the event_history collection."""
    text = _event_text(class_name, room, duration, summary)
    doc_id = f"event-{event_id}"
    metadata = {
        "event_id": event_id,
        "class_name": class_name,
        "timestamp": timestamp,
        "device_id": device_id or 0,
        "duration": duration,
        "confidence": confidence,
        "room": room,
    }
    try:
        collection = get_collection(_COLLECTION)
        upsert_texts(collection, texts=[text], metadatas=[metadata], ids=[doc_id])
        log.debug("Embedded event %d into %s", event_id, _COLLECTION)
    except Exception as exc:
        log.warning("Failed to embed event %d: %s", event_id, exc)


def retrieve_similar_events(query: str, k: int = 5) -> list[dict]:
    """Return up to k event documents most similar to the query string."""
    try:
        collection = get_collection(_COLLECTION)
        docs = collection.similarity_search(query, k=k)
        return [{"text": d.page_content, "metadata": d.metadata} for d in docs]
    except Exception as exc:
        log.warning("Event history retrieval failed: %s", exc)
        return []
