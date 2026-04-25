# Backend

FastAPI + LangChain + MCP + ChromaDB RAG + APScheduler memory layer.

## Setup

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp ../.env.example ../.env   # copy env config (edit if needed)
alembic upgrade head          # create/migrate the SQLite DB
```

## Run

```bash
uvicorn app.main:app --reload
# API docs: http://localhost:8000/docs
```

Ollama must be running before the backend starts:

```bash
ollama serve
ollama pull llama3.1:8b
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./soundsight.db` | SQLite (dev) or Postgres (prod) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API |
| `OLLAMA_MODEL` | `llama3.1:8b` | Model name |
| `CHROMA_PERSIST_DIR` | `./rag/chroma_data` | ChromaDB persistence directory |
| `ML_MODEL_PATH` | `../ml/artifacts/soundsight_classifier.joblib` | Trained classifier |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | Python logging level |

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/audio/classify` | Accept raw PCM bytes, return classification + LED/vibration |
| `GET` | `/api/events` | Paginated event list (`?limit`, `?offset`, `?class`, `?room`, `?from`, `?to`) |
| `POST` | `/api/events/{id}/explain` | (Re-)generate LLM explanation for an event |
| `WS` | `/ws/events` | WebSocket stream of live events |
| `GET` | `/api/reports/daily` | LLM-generated daily digest |
| `GET` | `/api/reports/weekly` | LLM-generated weekly digest |
| `POST` | `/api/rules` | Create alert rule (structured body or `{source_text}` for NL parsing) |
| `GET` | `/api/rules` | List all rules |
| `GET` | `/api/settings` | Read user profile / settings |
| `PUT` | `/api/settings` | Update notes, enabled classes, quiet hours |
| `POST` | `/api/devices/register` | Register a new ESP32 device |
| `GET` | `/api/devices` | List all registered devices |
| `GET` | `/api/devices/{id}` | Get a single device |
| `GET` | `/api/dashboard/summary` | Aggregate counts for the live dashboard |
| `POST` | `/api/onboarding/profile` | Generate + persist a sound profile from a home description |
| `GET/POST` | `/mcp/*` | MCP tool server (streamable HTTP) |

## Test

```bash
pytest                  # all tests
pytest tests/api/       # API endpoint tests only
pytest tests/services/  # LangChain chain + agent tests
pytest tests/mcp/       # MCP tool tests
```

All tests use an in-memory SQLite fixture — no running DB required.
