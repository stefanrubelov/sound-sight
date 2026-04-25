"""Collection 2 — Home Knowledge.

Stores the user's home description and profile notes as searchable embeddings.
Re-indexed whenever the user profile changes.
Used by event interpretation and anomaly narration to provide personalised context.
"""

from __future__ import annotations

import logging

from app.services.rag.chroma_client import get_collection, upsert_texts

log = logging.getLogger(__name__)

_COLLECTION = "home_knowledge"


def index_profile(
    profile_id: int,
    home_description: str | None,
    notes: str | None = None,
) -> None:
    """Upsert the user's profile text into the home_knowledge collection.

    Idempotent — safe to call every time the profile is saved.
    """
    chunks: list[str] = []
    ids: list[str] = []
    metadatas: list[dict] = []

    if home_description:
        chunks.append(home_description)
        ids.append(f"profile-{profile_id}-description")
        metadatas.append({"profile_id": profile_id, "section": "home_description"})

    if notes:
        chunks.append(notes)
        ids.append(f"profile-{profile_id}-notes")
        metadatas.append({"profile_id": profile_id, "section": "notes"})

    if not chunks:
        log.debug("No home knowledge to index for profile %d", profile_id)
        return

    try:
        collection = get_collection(_COLLECTION)
        upsert_texts(collection, texts=chunks, metadatas=metadatas, ids=ids)
        log.debug("Indexed %d home knowledge chunk(s) for profile %d", len(chunks), profile_id)
    except Exception as exc:
        log.warning("Failed to index home knowledge for profile %d: %s", profile_id, exc)


def retrieve_home_context(query: str, k: int = 3) -> str:
    """Return the most relevant home context snippets as a single string."""
    try:
        collection = get_collection(_COLLECTION)
        docs = collection.similarity_search(query, k=k)
        if not docs:
            return ""
        return "\n".join(d.page_content for d in docs)
    except Exception as exc:
        log.warning("Home knowledge retrieval failed: %s", exc)
        return ""
