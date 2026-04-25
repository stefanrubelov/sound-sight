"""Shared ChromaDB client and embedding function for all RAG collections."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

# Persistent storage at repo-level rag/chroma_data
_CHROMA_DIR = Path(__file__).parents[5] / "rag" / "chroma_data"

_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Module-level singletons — created on first use
_embeddings: "STEmbeddings | None" = None
_collections: dict[str, Chroma] = {}


class STEmbeddings(Embeddings):
    """Thin LangChain-compatible wrapper around sentence-transformers."""

    def __init__(self, model_name: str = _EMBEDDING_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        log.debug("Loaded sentence-transformer: %s", model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(text, convert_to_numpy=True).tolist()


def get_embeddings() -> STEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = STEmbeddings()
    return _embeddings


def get_collection(name: str) -> Chroma:
    """Return (creating if needed) a persistent Chroma collection by name."""
    if name not in _collections:
        _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _collections[name] = Chroma(
            collection_name=name,
            embedding_function=get_embeddings(),
            persist_directory=str(_CHROMA_DIR),
        )
        log.debug("Opened Chroma collection '%s' at %s", name, _CHROMA_DIR)
    return _collections[name]


def upsert_texts(
    collection: Chroma,
    texts: list[str],
    metadatas: list[dict],
    ids: list[str],
) -> None:
    """Upsert documents: delete existing ids then add.

    langchain-chroma's add_texts raises on duplicate IDs, so we remove first.
    """
    try:
        collection.delete(ids=ids)
    except Exception:
        pass  # ids may not exist yet — that is fine
    collection.add_texts(texts=texts, metadatas=metadatas, ids=ids)
