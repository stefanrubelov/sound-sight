# SoundSight — Repository Structure

> Directory layout for the SoundSight implementation. Read this before starting Phase 0 in `IMPLEMENTATION.md`.

## Top-level tree

```
soundsight/
├── README.md                          # top-level pitch + run instructions
├── IMPLEMENTATION.md                  # the build checklist
├── STRUCTURE.md                       # this file
├── DECISIONS.md                       # running log of design choices
├── docker-compose.yml                 # Postgres + ChromaDB for dev
├── .gitignore
├── .env.example
│
├── docs/
│   ├── SoundSight_Project_Plan_v2.pdf
│   ├── SoundSight_Pitch_v2.pdf
│   └── architecture.png               # exported diagram
│
├── backend/                           # ← FastAPI (API + AI orchestration live here)
│   ├── pyproject.toml
│   ├── README.md
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry
│   │   ├── config.py                  # pydantic-settings
│   │   ├── logging.py
│   │   ├── dependencies.py
│   │   ├── api/                       # REST routes
│   │   │   ├── audio.py
│   │   │   ├── events.py
│   │   │   ├── rules.py
│   │   │   ├── devices.py
│   │   │   ├── reports.py
│   │   │   ├── onboarding.py
│   │   │   ├── settings.py
│   │   │   └── websocket.py           # /ws/events
│   │   ├── schemas/                   # Pydantic request/response models
│   │   │   ├── event.py
│   │   │   ├── rule.py
│   │   │   └── ...
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── models.py              # SQLAlchemy models
│   │   └── services/                  # business logic
│   │       ├── ml/
│   │       │   └── classifier.py      # wraps ml/inference.py
│   │       ├── llm/                   # ← all AI orchestration
│   │       │   ├── ollama_client.py
│   │       │   ├── chains/
│   │       │   │   ├── rule_parser.py
│   │       │   │   ├── event_interpreter.py
│   │       │   │   └── onboarding_profiler.py
│   │       │   └── agents/
│   │       │       ├── report_generator.py
│   │       │       └── anomaly_narrator.py
│   │       ├── rag/
│   │       │   ├── chroma_client.py
│   │       │   ├── retrievers.py
│   │       │   └── indexers.py
│   │       ├── memory/
│   │       │   ├── session_memory.py
│   │       │   └── baseline_memory.py
│   │       └── mcp_client.py          # LangChain → MCP adapter
│   └── tests/
│       ├── conftest.py
│       ├── api/
│       ├── services/
│       └── integration/
│
├── frontend/                          # ← React + TS
│   ├── package.json
│   ├── vite.config.ts
│   ├── README.md
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── types.ts
│   │   ├── hooks/
│   │   │   └── useEvents.ts           # WebSocket hook
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── History.tsx
│   │   │   ├── Rules.tsx
│   │   │   ├── Devices.tsx
│   │   │   ├── Settings.tsx
│   │   │   ├── Onboarding.tsx
│   │   │   └── Reports.tsx
│   │   ├── components/
│   │   └── styles/
│   └── tests/
│
├── firmware/                          # ← ESP32 (IoT)
│   ├── platformio.ini
│   ├── README.md                      # wiring diagram, setup
│   ├── TESTING.md
│   ├── src/
│   │   ├── main.cpp
│   │   ├── audio.cpp / audio.h        # I2S capture
│   │   ├── network.cpp / network.h    # WiFi + HTTP POST
│   │   ├── actuators.cpp / .h         # LEDs + vibration
│   │   ├── config_portal.cpp / .h     # first-boot AP mode
│   │   └── display.cpp / .h           # optional OLED
│   └── test/                          # PlatformIO native-env tests
│
├── ml/                                # ← model training (separate from inference)
│   ├── README.md
│   ├── REPORT.md                      # accuracy, confusion matrix notes
│   ├── requirements.txt
│   ├── data/                          # gitignored
│   │   ├── esc50/
│   │   ├── us8k/
│   │   └── custom/
│   ├── preprocess.py
│   ├── train.py
│   ├── evaluate.py
│   ├── inference.py                   # Classifier class, imported by backend
│   └── artifacts/
│       ├── soundsight_classifier.joblib
│       └── confusion_matrix.png
│
├── mcp/                               # ← MCP server (context tools)
│   ├── README.md
│   ├── server.py                      # MCP server entry
│   └── tools/
│       ├── query_events.py
│       ├── get_device_status.py
│       ├── get_user_profile.py
│       ├── get_active_rules.py
│       ├── get_sound_class_info.py
│       └── get_user_baseline.py
│
├── rag/                               # ← RAG corpus + indexing scripts
│   ├── README.md
│   ├── corpus/
│   │   └── sound_classes/
│   │       ├── fire_alarm.md
│   │       ├── doorbell.md
│   │       ├── glass_breaking.md
│   │       └── ...                    # one per class
│   ├── index_sound_classes.py
│   └── chroma_data/                   # gitignored — ChromaDB persistence
│
├── prompts/                           # ← prompt templates + Promptfoo
│   ├── README.md
│   ├── base_system.md
│   ├── rule_parser.md
│   ├── event_interpreter.md
│   ├── onboarding_profiler.md
│   ├── report_generator.md
│   ├── anomaly_narrator.md
│   └── promptfoo/
│       ├── promptfooconfig.yaml
│       ├── rule_parser.yaml
│       ├── event_interpretation.yaml
│       ├── anomaly_narration.yaml
│       ├── onboarding_profiler.yaml
│       └── results/                   # saved baseline runs
│
├── ollama/                            # ← optional, only if we ship custom model
│   ├── Modelfile
│   └── README.md
│
└── scripts/
    ├── run_backend.sh
    ├── run_frontend.sh
    ├── run_promptfoo.sh
    ├── seed_db.py
    ├── inject_event.py                # demo backup — fake event injector
    └── rebuild_rag.sh
```

## Top-level directories at a glance

| Directory | What lives here | Who owns it |
|---|---|---|
| `backend/` | FastAPI app — REST routes, WebSocket, LangChain chains/agents, RAG retrievers, memory | Samuel |
| `frontend/` | React + TS SPA | Samuel |
| `firmware/` | ESP32 C/C++ firmware (PlatformIO) | Stefan |
| `ml/` | Model training, evaluation, inference wrapper | Stefan |
| `mcp/` | MCP server definition and tool implementations | Samuel |
| `rag/` | RAG corpus files + one-shot indexing scripts | Samuel |
| `prompts/` | Prompt templates + Promptfoo test suites | Stefan (Promptfoo), shared (templates) |
| `ollama/` | Optional custom Modelfile | Samuel |
| `scripts/` | Dev/demo helper scripts | Shared |
| `docs/` | Plan + pitch PDFs + architecture diagram | Shared |

## Design calls worth understanding

### `ml/` vs `backend/app/services/ml/`

`ml/` holds the *training* code — data prep, training loop, evaluation notebooks, saved model artifacts. `backend/app/services/ml/classifier.py` is a thin service-layer wrapper that imports `ml/inference.py` and exposes it to FastAPI. This way the training code can evolve independently and doesn't pollute the backend's runtime dependencies. The backend only needs `librosa` and the model artifact, not `matplotlib` or notebook tooling.

### `mcp/` as its own top-level directory

MCP stays out of `backend/` even though it runs in-process during the exam. The whole point of MCP is that it's a swappable boundary; putting it at the root signals that architecturally, and makes it trivial to split into its own process later without touching backend code. The backend talks to it via `backend/app/services/mcp_client.py`.

### `prompts/` as its own top-level directory

Prompts are versioned artifacts that get tested independently (Promptfoo). They're consumed by `backend/app/services/llm/` but they belong to the AI deliverable, not the backend code. Keeping them separate means prompt iteration doesn't require a backend rebuild, and Promptfoo can run against them directly.

### `rag/` holds corpus + indexing scripts, NOT retrieval code

The retrieval code lives in `backend/app/services/rag/` because it runs in the FastAPI process at request time. `rag/` at the root is just: source corpus files (markdown per sound class, seed home-knowledge) + the one-off scripts that push them into ChromaDB. ChromaDB's persistent data also lives under `rag/chroma_data/` but is gitignored.

### `firmware/` uses the standard PlatformIO layout

`src/` for source files, `test/` for native-env unit tests. `platformio.ini` at the root configures boards and environments. Nothing exotic — anyone with PlatformIO can build it.

### Why separate `schemas/` from `db/models.py`

Pydantic schemas (API request/response shapes) are different from SQLAlchemy models (DB table shapes). Keeping them in separate modules avoids circular imports and lets us evolve API contracts without DB migrations (and vice versa).

## What's gitignored

- `ml/data/` — training datasets are huge, don't commit them; provide download scripts
- `ml/artifacts/` — model weights (provide a release-tag or download link if needed)
- `rag/chroma_data/` — ChromaDB persistence, regenerated from corpus
- `backend/.venv/`, `frontend/node_modules/`, `firmware/.pio/`
- `.env` files (only `.env.example` is committed)
- `prompts/promptfoo/results/*.json` except baselines explicitly kept for comparison

## Cross-module import rules

To keep the architecture honest:

1. **`backend/` imports from `ml/inference.py`** — fine (thin interface)
2. **`backend/app/services/llm/` → `backend/app/services/mcp_client.py`** — agents reach MCP tools through the client adapter, never directly
3. **`backend/app/services/llm/` → `backend/app/services/rag/retrievers.py`** — chains pull context through retriever wrappers
4. **Nothing imports from `frontend/`, `firmware/`, or `prompts/`** — those are standalone deliverables
5. **`mcp/tools/` can import from `backend/app/db/`** — MCP tools are thin wrappers over DB queries; fine for the in-process setup. If we later split MCP into its own process, tools talk to the backend via HTTP instead.
