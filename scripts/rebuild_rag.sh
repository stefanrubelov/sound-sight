#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

source backend/.venv/bin/activate

echo "Rebuilding RAG corpus..."
python rag/index_sound_classes.py

echo "Done. ChromaDB data at rag/chroma_data/"
