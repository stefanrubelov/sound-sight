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

## Dev setup (required for every contributor)

After cloning, install the pre-commit hooks so linting runs automatically before every commit:

```bash
pip install pre-commit
pre-commit install
```

This installs four hooks: **black** + **ruff** (Python), **prettier** + **eslint** (TypeScript). They run on the files you changed — first commit after clone will be slightly slower while the hook environments download. Every commit after that is fast.

The same checks run in CI (GitHub Actions) on every push and pull request, so skipping `pre-commit install` just means CI will catch it instead.

## Team

Stefan Rubelov • Samuel Stiksa
