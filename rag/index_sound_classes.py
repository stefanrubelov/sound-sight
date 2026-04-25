#!/usr/bin/env python3.14
"""Build (or rebuild) the sound_class_kb ChromaDB collection from the corpus files.

Usage:
    python rag/index_sound_classes.py

Run this once during setup, or whenever the corpus Markdown files change.
"""

import sys
from pathlib import Path

# Make the backend package importable when run from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.rag.sound_class_kb import index_sound_classes

if __name__ == "__main__":
    corpus_dir = Path(__file__).parent / "corpus" / "sound_classes"
    n = index_sound_classes(corpus_dir)
    print(f"Indexed {n} sound-class document(s) into ChromaDB.")
