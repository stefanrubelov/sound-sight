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
**Why:** AI Apps subject requires Python. Also unifies ML training + inference in one language, removes the ONNX round-trip. Python 3.14 is the version available on dev machines (3.11 not installed).
**Alternatives considered:** C#/.NET 8 (original plan) — dropped due to subject requirement. Python 3.11 — not available on dev machines.

## 2026-04-22 — Ollama for LLM hosting
**Decision:** Local Ollama with `llama3.1:8b` as default.
**Why:** Subject requirement. Also: privacy (no user audio leaves the machine), works offline for demo, no API costs.
**Alternatives considered:** Claude/OpenAI API (original plan) — dropped due to subject requirement.

## 2026-04-22 — MCP as its own top-level directory
**Decision:** `mcp/` lives at the repo root, not under `backend/`.
**Why:** MCP is an architectural boundary; keeping it separate signals that and makes future process-splitting trivial.
**Alternatives considered:** `backend/app/mcp/` — rejected; it muddies the boundary.
