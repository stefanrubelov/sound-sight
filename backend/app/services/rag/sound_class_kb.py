"""Collection 3 — Sound-Class Knowledge Base.

Indexes the Markdown files in rag/corpus/sound_classes/ and exposes a retriever
for chains that need factual context about a sound class (description, safety
implications, common false positives).
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.services.rag.chroma_client import get_collection, upsert_texts

log = logging.getLogger(__name__)

_COLLECTION = "sound_class_kb"
_CORPUS_DIR = Path(__file__).parents[5] / "rag" / "corpus" / "sound_classes"


def _load_corpus(corpus_dir: Path) -> tuple[list[str], list[dict], list[str]]:
    texts, metadatas, ids = [], [], []
    for md_file in sorted(corpus_dir.glob("*.md")):
        class_name = md_file.stem
        content = md_file.read_text(encoding="utf-8").strip()
        if not content:
            continue
        texts.append(content)
        metadatas.append({"class_name": class_name, "source": md_file.name})
        ids.append(f"kb-{class_name}")
    return texts, metadatas, ids


def index_sound_classes(corpus_dir: Path | None = None) -> int:
    """Build (or rebuild) the sound_class_kb collection from the corpus directory.

    Returns the number of documents indexed.
    """
    corpus_dir = corpus_dir or _CORPUS_DIR
    texts, metadatas, ids = _load_corpus(corpus_dir)
    if not texts:
        log.warning("No corpus files found in %s", corpus_dir)
        return 0

    collection = get_collection(_COLLECTION)
    upsert_texts(collection, texts=texts, metadatas=metadatas, ids=ids)
    log.info("Indexed %d sound-class KB documents", len(texts))
    return len(texts)


def retrieve_class_info(class_name: str, k: int = 1) -> str:
    """Return KB content for the given class name.

    Falls back to a similarity search if an exact match is not found.
    """
    try:
        collection = get_collection(_COLLECTION)
        # Try exact doc first
        result = collection.get(ids=[f"kb-{class_name}"])
        if result and result.get("documents"):
            return result["documents"][0]
        # Fallback: similarity search
        docs = collection.similarity_search(class_name.replace("_", " "), k=k)
        return docs[0].page_content if docs else ""
    except Exception as exc:
        log.warning("Sound class KB retrieval failed for '%s': %s", class_name, exc)
        return ""
