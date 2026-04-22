# SoundSight — Initial Scaffold Guide

> One-time bootstrap steps to set up the repo skeleton before any real implementation begins. Run through this top-to-bottom, then make your "initial scaffold" commit and push. After that, hand the repo over to Claude Code to start `IMPLEMENTATION.md` Phase 1.

This is **not** the build checklist — it's the setup before the checklist. Expect this to take ~1–2 hours.

---

## 0. Prerequisites check

Before you start, make sure these are installed. Versions are what we're targeting; close-enough is fine.

- [ ] Git
- [ ] Python 3.14 (`python3.14 --version`)
- [ ] Node.js 20+ (`node --version`)
- [ ] PlatformIO Core (`pio --version`) — install via `pip install platformio` or the VS Code extension
- [ ] Docker + Docker Compose (`docker --version`) — optional but tidy for Postgres/Chroma
- [ ] Ollama (`ollama --version`) — install from [ollama.com](https://ollama.com)
- [ ] A code editor — VS Code recommended for the PlatformIO integration

Quick verifications:

```bash
python3.14 --version
node --version
pio --version
ollama --version
```

---

## 1. Create the repo

```bash
mkdir soundsight && cd soundsight
git init -b main
```

---

## 2. Create the directory skeleton

One command to lay down every directory from `STRUCTURE.md`:

```bash
mkdir -p \
  docs \
  backend/app/{api,schemas,db,services/{ml,llm/{chains,agents},rag,memory}} \
  backend/alembic/versions \
  backend/tests/{api,services,integration} \
  frontend/src/{api,hooks,pages,components,styles} \
  frontend/tests \
  firmware/src \
  firmware/test \
  ml/{data/{esc50,us8k,custom},artifacts} \
  mcp/tools \
  rag/{corpus/sound_classes,chroma_data} \
  prompts/promptfoo/results \
  ollama \
  scripts
```

Add `.gitkeep` files so empty dirs get committed:

```bash
find . -type d -empty -not -path './.git/*' -exec touch {}/.gitkeep \;
```

---

## 3. Root-level files

### `.gitignore`

```bash
cat > .gitignore <<'EOF'
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.ruff_cache/
.mypy_cache/

# Node
node_modules/
dist/
.vite/

# PlatformIO
.pio/
.pioenvs/
.piolibdeps/

# ML artifacts & data
ml/data/esc50/*
ml/data/us8k/*
ml/data/custom/*
!ml/data/**/.gitkeep
ml/artifacts/*.joblib
ml/artifacts/*.pt
ml/artifacts/*.onnx

# RAG / Chroma
rag/chroma_data/*
!rag/chroma_data/.gitkeep

# Promptfoo (keep baselines explicitly)
prompts/promptfoo/results/*.json

# Env files
.env
.env.local
*.env

# OS / editor
.DS_Store
.idea/
.vscode/
!.vscode/settings.json.example

# Logs
*.log
EOF
```

### `.env.example`

```bash
cat > .env.example <<'EOF'
# Backend
DATABASE_URL=sqlite+aiosqlite:///./soundsight.db
# DATABASE_URL=postgresql+asyncpg://soundsight:soundsight@localhost:5432/soundsight
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# ChromaDB
CHROMA_PERSIST_DIR=./rag/chroma_data

# Frontend (prefix with VITE_ to expose to the browser)
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/events
EOF
cp .env.example .env
```

### `README.md`

```bash
cat > README.md <<'EOF'
# SoundSight

AI-powered sound awareness for the hearing impaired. Combined final exam project: AI Apps + IoT.

## What it is

SoundSight turns any room into a hearing-accessible environment. ESP32 + microphone nodes capture environmental sounds, a Python backend classifies them with ML, and a locally-hosted LLM (orchestrated by LangChain, grounded by RAG, backed by memory) adds contextual intelligence on top. Alerts reach the user via LEDs, vibration, and a fully accessible web dashboard.

## Stack

- **IoT:** ESP32 + INMP441 I2S mic + WS2812B LEDs + vibration motor, firmware in C/C++ (PlatformIO)
- **Backend:** Python 3.14 + FastAPI, WebSocket for real-time events
- **AI:** Ollama (local LLM) + LangChain orchestration + MCP tool layer + ChromaDB RAG + memory
- **Frontend:** React + TypeScript (Vite)
- **Testing:** pytest + Vitest + Promptfoo
- **Database:** PostgreSQL (prod) / SQLite (dev)

## Repo layout

See [`STRUCTURE.md`](./STRUCTURE.md).

## Build plan

See [`IMPLEMENTATION.md`](./IMPLEMENTATION.md) for the phase-by-phase checklist.

## Quick start

```bash
# Backend
cd backend && python3.14 -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Firmware
cd firmware && pio run -t upload && pio device monitor

# Ollama
ollama serve
ollama pull llama3.1:8b
```

## Team

Stefan Rubelov • Samuel Stiksa
EOF
```

### `DECISIONS.md`

```bash
cat > DECISIONS.md <<'EOF'
# Design Decisions Log

Running record of non-obvious design calls. Append new entries at the top.

Format:
```
## YYYY-MM-DD — short title
**Decision:** what we decided
**Why:** the reasoning
**Alternatives considered:** what we rejected and why
```

## 2026-04-22 — Python/FastAPI over C#/.NET
**Decision:** Backend is Python 3.14 + FastAPI.
**Why:** AI Apps subject requires it. Also unifies ML training + inference in one language, removes the ONNX round-trip.
**Alternatives considered:** C#/.NET 8 (original plan) — dropped due to subject requirement.

## 2026-04-22 — Ollama for LLM hosting
**Decision:** Local Ollama with `llama3.1:8b` as default.
**Why:** Subject requirement. Also: privacy (no user audio leaves the machine), works offline for demo, no API costs.
**Alternatives considered:** Claude/OpenAI API (original plan) — dropped due to subject requirement.

## 2026-04-22 — MCP as its own top-level directory
**Decision:** `mcp/` lives at the repo root, not under `backend/`.
**Why:** MCP is an architectural boundary; keeping it separate signals that and makes future process-splitting trivial.
**Alternatives considered:** `backend/app/mcp/` — rejected; it muddies the boundary.
EOF
```

### `docker-compose.yml` (optional)

```bash
cat > docker-compose.yml <<'EOF'
version: "3.9"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: soundsight
      POSTGRES_PASSWORD: soundsight
      POSTGRES_DB: soundsight
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
EOF
```

(ChromaDB runs embedded in the backend process — no separate container needed.)

---

## 4. Backend scaffolding

```bash
cd backend
```

### `pyproject.toml`

```bash
cat > pyproject.toml <<'EOF'
[project]
name = "soundsight-backend"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "pydantic>=2.9",
  "pydantic-settings>=2.6",
  "sqlalchemy>=2.0",
  "alembic>=1.13",
  "aiosqlite>=0.20",
  "asyncpg>=0.30",
  "python-multipart>=0.0.12",
  "websockets>=13",
  "langchain>=0.3",
  "langchain-ollama>=0.2",
  "langchain-chroma>=0.1",
  "langchain-mcp-adapters>=0.1",
  "sentence-transformers>=3.2",
  "chromadb>=0.5",
  "librosa>=0.10",
  "numpy>=1.26",
  "scikit-learn>=1.5",
  "joblib>=1.4",
  "apscheduler>=3.10",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
  "httpx>=0.27",
  "ruff>=0.7",
  "black>=24.10",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
EOF
```

### Placeholder `app/main.py`

```bash
cat > app/main.py <<'EOF'
"""SoundSight backend entry point. Placeholder — real routes come in Phase 1."""
from fastapi import FastAPI

app = FastAPI(title="SoundSight", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
EOF

touch app/__init__.py
```

### Placeholder `backend/README.md`

```bash
cat > README.md <<'EOF'
# Backend

FastAPI + LangChain + MCP + RAG.

## Setup

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```
EOF
```

Back to root:
```bash
cd ..
```

---

## 5. Frontend scaffolding

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

Add a minimal `frontend/README.md`:
```bash
cat > README.md <<'EOF'
# Frontend

React + TypeScript (Vite).

## Setup

```bash
npm install
```

## Run dev server

```bash
npm run dev
```

## Test

```bash
npm test
```
EOF
```

Back to root:
```bash
cd ..
```

---

## 6. Firmware scaffolding

```bash
cd firmware
pio project init --board esp32dev
```

Edit `platformio.ini` to pin libraries we'll need later (they won't pull until first build):

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
lib_deps =
  fastled/FastLED@^3.7.0
  bblanchon/ArduinoJson@^7.2.0
  https://github.com/tzapu/WiFiManager.git
```

Minimal `src/main.cpp`:
```cpp
#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  Serial.println("SoundSight firmware — scaffold only");
}

void loop() {
  delay(1000);
}
```

Add `firmware/README.md`:
```bash
cat > README.md <<'EOF'
# Firmware

ESP32 firmware for SoundSight audio nodes.

## Hardware

- ESP32 WROOM (or S3)
- INMP441 I2S digital microphone
- WS2812B LED strip
- Vibration motor (via MOSFET)
- Optional: SSD1306 OLED

## Build & upload

```bash
pio run -t upload
pio device monitor
```

## Wiring

TBD — added in Phase 2.
EOF
```

Back to root:
```bash
cd ..
```

---

## 7. Copy docs into the repo

Place the PDFs and markdown guides in their homes:

```bash
# From wherever the files currently live on your machine
cp /path/to/SoundSight_Project_Plan_v2.pdf docs/
cp /path/to/SoundSight_Pitch_v2.pdf docs/
cp /path/to/IMPLEMENTATION.md .
cp /path/to/STRUCTURE.md .
cp /path/to/SCAFFOLD.md .   # this file
```

---

## 8. Verification

Before committing, confirm the three sub-projects at least boot:

```bash
# Backend
cd backend
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload &
sleep 2
curl http://localhost:8000/health   # → {"status":"ok"}
kill %1
deactivate
cd ..

# Frontend
cd frontend
npm run dev &
sleep 3
curl -I http://localhost:5173   # → 200 OK
kill %1
cd ..

# Firmware — just confirm it compiles, don't flash anything yet
cd firmware
pio run
cd ..

# Ollama — confirm the base model is pulled
ollama pull llama3.1:8b
ollama list
```

If all four pass, the scaffold is working.

---

## 9. Initial commit

```bash
git add .
git commit -m "chore: initial scaffold

- Repo structure per STRUCTURE.md
- Backend: FastAPI skeleton with /health
- Frontend: Vite + React + TS skeleton
- Firmware: PlatformIO ESP32 skeleton
- Docs: plan + pitch PDFs, IMPLEMENTATION and STRUCTURE guides
"
```

Create the remote (GitHub/GitLab/whatever you use) and push:

```bash
git remote add origin git@github.com:yourname/soundsight.git
git branch -M main
git push -u origin main
```

---

## 10. Hand-off to Claude Code

From this point, open the repo in Claude Code and point it at `IMPLEMENTATION.md`:

> "Read `STRUCTURE.md`, `IMPLEMENTATION.md`, and `DECISIONS.md`. We've finished Phase 0 bootstrap. Start Phase 1: Backend Skeleton."

Everything from here is tracked in `IMPLEMENTATION.md`. Check boxes as you go, log non-obvious design calls in `DECISIONS.md`.

---

## Common bootstrap gotchas

- **`pip install` fails on `sentence-transformers`** — needs a C compiler on some platforms. On macOS install Xcode CLT; on Linux `apt install build-essential`.
- **`ollama pull` takes forever** — the 8B model is ~5 GB. Do it on good WiFi, not tethered.
- **PlatformIO can't find the ESP32** — the USB-to-serial chip (CP210x or CH340) often needs a driver on macOS/Windows. Linux works out of the box.
- **Vite dev server port collision** — 5173 is default; if it's taken, Vite will pick 5174 and the `.env` `VITE_*` URLs + CORS settings need updating.
- **Postgres container won't start** — check `docker ps` for port 5432 conflicts with a system Postgres.
