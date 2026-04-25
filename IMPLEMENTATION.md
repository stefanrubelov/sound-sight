# SoundSight — Implementation Checklist

> Implementation guide for Claude Code. Work top-to-bottom within each phase; phases can overlap across partners once Phase 0 is done. Check items off as you complete them.

**Stack reference:** ESP32 (C/C++) • Python 3.14 + FastAPI • React + TypeScript (Vite) • Ollama • LangChain • MCP • ChromaDB • PostgreSQL/SQLite • Promptfoo • pytest + Vitest

**Partner split (suggested, see Plan §17):**
- **Stefan (A):** ESP32 firmware, ML training + inference, audio preprocessing, hardware, Promptfoo
- **Samuel (B):** FastAPI, LangChain + Ollama, MCP + RAG, React frontend, memory, unit test infrastructure

Both partners must understand the full system for exam defense.

---

## Phase 0 — Project Bootstrap (Day 1)

### Repository & tooling
- [x] Create Git repo with top-level structure:
  - [x] `backend/` — FastAPI app
  - [x] `frontend/` — React + TS (Vite)
  - [x] `firmware/` — PlatformIO project for ESP32
  - [x] `ml/` — training scripts, notebooks, model artifacts
  - [x] `prompts/` — LangChain prompt templates + Promptfoo config
  - [x] `mcp/` — MCP server definition
  - [x] `rag/` — corpus files + indexing scripts
  - [x] `docs/` — this checklist + project plan PDFs
  - [x] `scripts/` — dev/run/demo helper scripts
- [x] Add `.gitignore` for Python, Node, PlatformIO, `.env`, ChromaDB data, model weights
- [x] Add root `README.md` with setup instructions (will fill in as we go)
- [x] Decide on branch strategy (suggest: `main` + short-lived feature branches)
- [x] Set up pre-commit hooks (black + ruff for Python, prettier + eslint for TS)

### Dev environment
- [x] Pin Python 3.14; add `backend/pyproject.toml` (or `requirements.txt`)
- [x] Node 20+ for frontend
- [x] PlatformIO installed for firmware
- [x] Install Ollama locally, pull base model: `ollama pull llama3.1:8b` (or `qwen2.5:7b-instruct`)
- [x] Verify Ollama is reachable: `curl http://localhost:11434/api/tags`
- [x] PostgreSQL running locally (Docker compose fine) OR decide to start on SQLite
- [x] Add `docker-compose.yml` for Postgres + ChromaDB (optional but tidy)

### Shared docs
- [x] Drop `SoundSight_Project_Plan_v2.pdf` and `SoundSight_Pitch_v2.pdf` into `docs/`
- [x] Keep this `IMPLEMENTATION.md` at repo root

---

## Phase 1 — Backend Skeleton (Week 1, Samuel)

### FastAPI scaffold
- [x] `backend/app/main.py` with FastAPI app instance
- [x] CORS middleware configured for the frontend origin
- [x] `/health` endpoint returning `{status: "ok"}`
- [x] Uvicorn dev script: `uvicorn app.main:app --reload`
- [x] `app/config.py` — settings via pydantic-settings, loaded from `.env`
- [x] `app/logging.py` — structured logging setup (json or rich)

### Project structure
- [x] `app/api/` — route modules (events, rules, devices, reports, onboarding, audio)
- [x] `app/services/` — business logic (ml, llm, rag, memory)
- [x] `app/db/` — SQLAlchemy models + session
- [x] `app/schemas/` — Pydantic request/response schemas
- [x] `app/dependencies.py` — FastAPI dependencies (DB session, auth placeholder)
- [x] `tests/` — pytest structure mirroring `app/`

### Database
- [x] SQLAlchemy 2.x setup, async engine
- [x] Alembic initialized, first migration
- [x] Models defined:
  - [x] `Device` (id, name, room, registered_at, last_seen)
  - [x] `Event` (id, device_id, class_name, confidence, timestamp, duration, raw_features, llm_summary)
  - [x] `Rule` (id, trigger, time_start, time_end, priority, alert_type, source_text, created_at)
  - [x] `UserProfile` (id, home_description, enabled_classes, quiet_hours, notes)
  - [x] `Baseline` (id, class_name, stats_json, updated_at) — for memory layer
- [x] Seed script: insert a default user profile + sample device for dev
- [x] Choose Postgres or SQLite per environment via config

### WebSocket
- [x] `/ws/events` endpoint with connection manager
- [x] Broadcast helper: `await ws_manager.broadcast(event_payload)`
- [x] Test with a tiny HTML client or `websocat`

### Unit tests
- [x] pytest + `httpx.AsyncClient` set up
- [x] `TestClient` smoke test for `/health`
- [x] In-memory SQLite fixture for test DB

---

## Phase 2 — ESP32 Firmware (Week 1, Stefan)

### PlatformIO project
- [x] `firmware/platformio.ini` — board = `esp32dev` (or `esp32-s3-devkitc-1`), framework = `arduino`
- [x] Libraries: `FastLED` (WS2812B), `ArduinoJson`, `WiFiManager` (config portal), optional `U8g2` (OLED)
- [ ] Build + upload blink sketch to verify toolchain

### I2S microphone (INMP441)
- [ ] Wire INMP441 to ESP32 (SCK, WS, SD pins documented)
- [x] I2S driver configured: 16 kHz, 16-bit, mono, left channel
- [ ] Capture 1-second buffer and log RMS to serial — confirm it reacts to sound
- [x] Handle DC offset / bit-shifting from I2S (INMP441 is 24-bit in 32-bit frames)

### WiFi + config portal
- [x] First-boot AP mode via WiFiManager
- [x] Fields: WiFi SSID + password, backend URL, device name, room name
- [x] Persist config to NVS/Preferences
- [x] Reset button / long-press to re-enter config mode

### HTTP POST pipeline
- [x] Send raw PCM bytes to `POST /api/audio/classify` (Content-Type: `application/octet-stream`)
- [x] Parse JSON response: `{event_type, severity, led_color, vibration_pattern}`
- [x] Error handling: retry with backoff, queue-or-drop policy on network failure

### Actuator drivers
- [x] WS2812B LED driver — set color, hold N seconds, fade out
- [x] Color map per event type (red, blue, yellow, green, white)
- [x] Vibration motor driver — PWM patterns: short pulse / double pulse / continuous
- [ ] Optional: SSD1306 OLED — show last event + timestamp

### Device registration
- [x] On first boot after WiFi is up, POST `/api/devices/register` with name + room → store returned `device_id`
- [x] Include `device_id` in every `/api/audio/classify` call

### Firmware "unit" testing
- [x] PlatformIO native-env tests for LED color map, vibration pattern selector (pure logic, no HW)
- [x] Manual test checklist in `firmware/TESTING.md`

---

## Phase 3 — ML Pipeline (Week 2, Stefan)

### Data
- [x] Download ESC-50 into `ml/data/esc50/` — script: `python ml/download_data.py --esc50`
- [x] Download UrbanSound8K into `ml/data/us8k/` — manual (requires registration); `download_data.py` verifies path
- [x] Record 5–10 custom clips per target class (our doorbell, our smoke detector, etc.) — place in `ml/data/custom/<class_name>/`
- [x] Finalize class list (6–8 classes): `fire_alarm`, `doorbell`, `glass_breaking`, `baby_crying`, `dog_barking`, `timer_beep`, `water_running`, `unknown`

### Preprocessing (`ml/preprocess.py`)
- [x] Load audio with librosa, resample to 16 kHz mono
- [x] Window into 1-second clips with 50% overlap
- [x] Feature extraction: MFCC (40 coeffs) — chosen for compact vectors + sklearn compatibility (documented in file + REPORT.md)
- [x] Save features + labels as `.npz` per split

### Training (`ml/train.py`)
- [x] Train/val/test split (stratified)
- [x] Model choice: RandomForestClassifier (sklearn) on MFCCs — fast, no GPU needed
- [x] Train loop with metrics logging
- [x] Save model to `ml/artifacts/soundsight_classifier.joblib`

### Evaluation (`ml/evaluate.py`)
- [x] Confusion matrix (save as PNG for the presentation)
- [x] Per-class precision / recall / F1
- [x] Overall accuracy
- [x] Confidence distribution plot (to help pick the "unknown" threshold)
- [x] Write `ml/REPORT.md` summarizing results

### Inference wrapper (shared with backend)
- [x] `ml/inference.py` — `Classifier` class with `.predict(pcm_bytes) -> ClassificationResult`
- [x] Applies the *exact same* preprocessing as training
- [x] Returns `{class_name, confidence, all_scores}`
- [x] If top confidence < threshold → return `class_name="unknown"`

### Tests
- [x] Unit: preprocessing (shape, dtype, silence handling)
- [x] Unit: classifier wrapper (mock model, fake PCM)
- [x] Integration: run end-to-end on a known test clip and assert predicted class

---

## Phase 4 — Classification Endpoint (Week 2, Samuel + Stefan)

- [x] `POST /api/audio/classify` — accept raw bytes, call `Classifier`, persist `Event`
- [x] Broadcast new event over `/ws/events`
- [x] Response payload includes `led_color` + `vibration_pattern` (mapped from class + severity)
- [x] Severity lookup table: config-driven (critical/warn/info per class) — in `app/config.py`
- [x] Handle `unknown` class: low-severity response, don't trigger alerts
- [x] Write LLM summary *asynchronously* (don't block the ESP32 response)
- [x] Unit tests for the endpoint (TestClient + mocked classifier)

---

## Phase 5 — Frontend Skeleton (Week 1–2, Samuel)

### Vite + React + TS setup
- [x] `npm create vite@latest frontend -- --template react-ts` — already scaffolded
- [x] Router (React Router v7), base layout with `<Outlet>`, navigation
- [x] CSS modules chosen over Tailwind — no build-time dependency, consistent with existing CSS
- [x] Accessibility baseline: keyboard focus rings (`focus-visible`), `prefers-reduced-motion`, ARIA landmarks

### API client
- [x] `src/api/client.ts` — typed fetch wrapper, base URL from `VITE_API_URL` env
- [x] Types in `src/api/types.ts`: Event, Rule, Device, UserProfile, ClassifyResponse, filters
- [x] `src/hooks/useEvents.ts` — WebSocket hook with auto-reconnect

### Pages (placeholders first, fill in through Week 3)
- [x] **Live dashboard** — real-time event cards with severity colour-coding
- [x] **History** — paginated event list, filters (class, date range)
- [x] **Rules** — list + NL text box → `POST /api/rules`
- [x] **Devices** — registered devices list
- [x] **Settings** — profile notes, shows enabled classes + quiet hours
- [x] **Onboarding** — home description → profile preview
- [x] **Reports** — daily + weekly LLM digest tabs

### Accessibility pass
- [x] High contrast mode toggle (`data-theme="high-contrast"` on `<html>`)
- [x] Large text mode toggle (`data-size="large"` on `<html>`)
- [x] All interactive elements reachable by keyboard (focus-visible outlines on all controls)
- [x] No audio-only feedback anywhere (no sounds, no speech)

### Tests
- [x] Vitest + React Testing Library set up (`vitest.config.ts`, `tests/setup.ts`)
- [x] Smoke test for each page renders without crash (`tests/pages.test.tsx`, 12 tests)
- [x] Filter logic test for history page (`tests/historyFilter.test.ts`, 6 tests)

---

## Phase 6 — LLM Layer: Ollama + LangChain (Week 3, Samuel)

### Ollama integration
- [x] `app/services/llm/ollama_client.py` — wraps `langchain_ollama.ChatOllama`
- [x] Model + temperature configurable per chain
- [x] Retry/timeout policy (asyncio.wait_for at call sites)

### Shared base system prompt
- [x] `prompts/base_system.md` — persona, tone, JSON-only-when-asked, no-hallucinations
- [x] Loader utility that merges base + role-specific prompt (`app/services/llm/prompt_loader.py`)

### Chain 1: Rule Parser (LCEL)
- [x] `app/services/llm/chains/rule_parser.py`
- [x] `ParsedRule` Pydantic schema with field validators
- [x] Prompt: system + format instructions + 5 few-shot examples
- [x] Temperature 0
- [x] `parse_rule(nl_text) -> ParsedRule`
- [x] Wire into `POST /api/rules` when body contains `source_text`
- [x] Unit tests with `FakeListChatModel`

### Chain 2: Event Interpretation (LCEL)
- [x] Input: Event + device info + user profile notes
- [x] Output: short natural-language summary (1–2 sentences)
- [x] Called async after each event insert via background task; writes to `Event.llm_summary`
- [x] Unit tests

### Chain 3: Onboarding Profiler (LCEL)
- [x] `SoundProfile` Pydantic schema (enabled_classes, priorities, quiet_hours_default)
- [x] Few-shot examples for 3 home archetypes (single person, family with baby, elderly alone)
- [x] `POST /api/onboarding/profile` → returns profile + persists to `UserProfile`
- [x] Unit tests

### Agent 1: Report Generation
- [x] Tools: `_query_events`, `_query_baselines`, `_query_rules` (direct DB — MCP wiring in Phase 7)
- [x] System prompt emphasizes outline → narrative
- [x] `GET /api/reports/daily` and `/weekly`
- [x] Cache reports for the day/week (in-memory dict)
- [x] Unit tests

### Agent 2: Anomaly Narration
- [x] Triggered when duration > 3σ from baseline
- [x] Queries `Baseline` table and generates contextual narration
- [x] Appended to `Event.llm_summary` when anomaly detected
- [x] Unit tests

### LLM decision: standard vs custom Ollama model
- [ ] Run Promptfoo (see Phase 9) against both `llama3.1:8b` and `qwen2.5:7b-instruct`
- [x] Write `ollama/Modelfile` baking in the base system prompt
- [ ] Build with `ollama create soundsight-base -f Modelfile` (run when Ollama available)
- [x] Modelfile committed as a deliverable

---

## Phase 7 — MCP Service Layer (Week 3, Samuel)

### MCP server
- [ ] `mcp/server.py` — MCP server using the official Python SDK
- [ ] Runs in-process with FastAPI during the exam
- [ ] Each tool: typed input schema, typed output, docstring used as description

### Tools to implement
- [ ] `query_events(filter, time_range) -> list[Event]`
- [ ] `get_device_status(device_id) -> DeviceStatus`
- [ ] `get_user_profile() -> UserProfile`
- [ ] `get_active_rules() -> list[Rule]`
- [ ] `get_sound_class_info(class_name) -> ClassInfo` (reads from the sound-class KB)
- [ ] `get_user_baseline(class_name, window) -> Baseline`

### LangChain integration
- [ ] `langchain-mcp-adapters` wired up; agents can see the tools via `ToolNode` or equivalent
- [ ] Verify tool calls end-to-end with a scripted agent test

### Tests
- [ ] Unit test each MCP tool in isolation (against test DB)
- [ ] Integration test: agent → MCP client → tool → DB → response

---

## Phase 8 — RAG (Week 3, Samuel)

### ChromaDB setup
- [ ] `rag/chroma_client.py` — embedded ChromaDB instance, persistent dir
- [ ] Embedding function: `sentence-transformers/all-MiniLM-L6-v2`

### Collection 1: Event History
- [ ] On every new event, generate a short NL summary and embed it
- [ ] Metadata: `class_name`, `timestamp`, `device_id`, `duration`, `confidence`
- [ ] Retriever wrapper for LangChain
- [ ] Used by: report generation, anomaly narration

### Collection 2: Home Knowledge
- [ ] Index the user's onboarding profile text + any notes
- [ ] Re-indexed whenever the profile changes (hook on update)
- [ ] Used by: event interpretation, anomaly narration

### Collection 3: Sound-Class KB
- [ ] `rag/corpus/sound_classes/*.md` — one file per sound class with: description, typical scenarios, safety implications, common false positives
- [ ] Versioned in the repo; `rag/index_sound_classes.py` script to (re)build
- [ ] Used by: event interpretation on medium-confidence cases

### Tests
- [ ] Unit: retriever returns top-k on fixed mini-corpus
- [ ] Integration: chain call actually uses retrieved context (snapshot test on prompt rendering)

---

## Phase 9 — Memory (Week 3, Samuel)

### Short-term (session buffer)
- [ ] `ConversationBufferWindowMemory` attached to interactive rule-creation flow
- [ ] Keyed by session ID (browser-generated UUID)
- [ ] Cleared on session end

### Long-term (user baselines)
- [ ] Nightly job (APScheduler or cron) that recomputes baselines from last 30 days of events per class
- [ ] Stats per `(class_name, user)`: count/day, typical time window, typical duration, night vs day ratio
- [ ] Stored in `Baseline` table
- [ ] Also embedded + stored in Chroma for agent retrieval
- [ ] Exposed via `get_user_baseline` MCP tool

### Tests
- [ ] Unit: baseline computation from a fixture of events
- [ ] Unit: memory doesn't leak across sessions

---

## Phase 10 — Promptfoo Testing (Week 3, Stefan)

### Setup
- [ ] Install Promptfoo: `npm i -g promptfoo`
- [ ] `prompts/promptfoo/promptfooconfig.yaml`
- [ ] Provider: local Ollama (`ollama:chat:llama3.1:8b`)

### Test suites
- [ ] **Rule parser** — `prompts/promptfoo/rule_parser.yaml`
  - [ ] 15+ golden input/output pairs
  - [ ] Cover: affirmative, negation, ambiguous times, multi-trigger, conflicting rules
  - [ ] Assertion type: strict JSON equality or field-level match
- [ ] **Event interpretation** — rubric-based (LLM-graded)
  - [ ] Must mention: duration, user context, no invented facts
- [ ] **Anomaly narration** — rubric-based
  - [ ] Must reference baseline, no false urgency
- [ ] **Onboarding profiler** — golden pairs
  - [ ] Home description → expected enabled classes

### CI / local gate
- [ ] `scripts/run_promptfoo.sh` — run all suites, fail on regressions
- [ ] Add to pre-merge checklist (or CI if time permits)
- [ ] Save baseline run output to repo for comparison

---

## Phase 11 — API Endpoints Build-out (Week 2–3)

Run through this list and make sure each endpoint is implemented + tested:

- [ ] `POST /api/audio/classify`
- [ ] `GET /api/events` (pagination: `?limit=&offset=&class=&room=&from=&to=`)
- [ ] `WS /ws/events`
- [ ] `GET /api/reports/daily`
- [ ] `GET /api/reports/weekly`
- [ ] `POST /api/rules` (accepts either structured body OR `{source_text: "..."}`)
- [ ] `GET /api/rules`
- [ ] `PUT /api/settings`
- [ ] `POST /api/devices/register`
- [ ] `GET /api/devices`
- [ ] `GET /api/dashboard/summary`
- [ ] `POST /api/onboarding/profile`
- [ ] `POST /api/events/{id}/explain` — on-demand LLM explanation

Each endpoint:
- [ ] Has a Pydantic request schema
- [ ] Has a Pydantic response schema
- [ ] Has at least one pytest test (happy path)
- [ ] Has a sad-path test (bad input / missing resource)

---

## Phase 12 — Frontend Build-out (Week 3, Samuel)

Hook the React pages up to real API data:

- [ ] Live dashboard reads from `/ws/events`, shows color-coded cards
- [ ] History page uses `/api/events` with filters
- [ ] Rules page: structured form + NL text box → `/api/rules`
- [ ] Devices page lists from `/api/devices`
- [ ] Settings page reads + writes `/api/settings`
- [ ] Onboarding page posts to `/api/onboarding/profile` and shows the generated profile
- [ ] Reports page fetches `/api/reports/daily` and `/weekly`, renders markdown
- [ ] Trend charts on dashboard home (Recharts or Chart.js)
- [ ] Loading + error states everywhere
- [ ] Empty states: friendly message when no events yet

---

## Phase 13 — Unit Test Coverage Pass (Week 4)

Target: every core component has at least one unit test.

### Backend (pytest)
- [ ] Audio preprocessing
- [ ] Classifier wrapper
- [ ] All API endpoints (happy + 1 sad path each)
- [ ] All LangChain chains (mocked LLM)
- [ ] All MCP tools
- [ ] RAG retrievers
- [ ] Baseline computation
- [ ] Session memory isolation

### Frontend (Vitest + RTL)
- [ ] Each page renders
- [ ] WebSocket hook dispatches to store
- [ ] Filter logic
- [ ] Accessibility props present on interactive elements

### Firmware
- [ ] Native-env tests for pure-logic helpers
- [ ] Document manual test steps in `firmware/TESTING.md`

---

## Phase 14 — Integration Testing (Week 4)

- [ ] End-to-end smoke: pre-recorded WAV → `POST /api/audio/classify` → WebSocket event visible in frontend
- [ ] End-to-end with real ESP32: clap next to mic → LED + dashboard card
- [ ] LLM pipeline: trigger event → `llm_summary` populated within N seconds
- [ ] Daily report: seed fake events → `GET /api/reports/daily` returns coherent narrative
- [ ] Rule parsing: type "Vibrate urgently if glass breaks after 22:00" → correct structured Rule
- [ ] Anomaly narration: inject an event with unusual duration → narration references baseline
- [ ] Network drop: kill WiFi mid-session, verify ESP32 reconnects and the backend recovers gracefully
- [ ] Unknown sound: play white noise → classified as `unknown`, no alert triggered

---

## Phase 15 — Demo Prep (Week 4)

### Demo kit
- [ ] Hardware in a presentable enclosure (or at least tidy wiring)
- [ ] Pre-recorded audio clips on a phone: doorbell, fire alarm, timer beep, glass break, baby crying
- [ ] Test endpoint `POST /api/dev/inject_event` for simulating events if live detection is flaky
- [ ] Seeded database with 1–2 weeks of plausible events (for the reports demo)
- [ ] Backup laptop / tethered hotspot in case campus WiFi is unreliable

### Demo script
- [ ] Write out the 5–7 minute flow (see Plan §16) step by step
- [ ] Mark fallback points ("if X fails, show Y instead")
- [ ] Rehearse twice with a timer

### Slides
- [ ] Title slide
- [ ] Problem (430M people, existing solutions gap)
- [ ] Demo transition slide
- [ ] Architecture diagram (from Plan §5.1)
- [ ] AI pipeline detail: LangChain + MCP + RAG + memory + Ollama
- [ ] Promptfoo results screenshot — proof the LLM is tested
- [ ] ML model accuracy + confusion matrix
- [ ] Future expansion (sound direction, wearable, smart home)
- [ ] Team slide

### Q&A prep (both partners)
- [ ] Why Ollama instead of API? (privacy, cost, works offline for demo)
- [ ] Why MCP? (separation of reasoning from data access; reusable)
- [ ] Why RAG? (ground LLM in real event history + user context)
- [ ] Why local memory not chatbot? (baselines are structured, not conversational)
- [ ] Why FastAPI over Flask/Django? (async, typed, OpenAPI-first, WebSocket native)
- [ ] Why these ML classes? (safety-first selection + what we have training data for)
- [ ] Why clock-sync doesn't work for multi-node TDOA? (WiFi NTP jitter > acoustic window)

---

## Phase 16 — Polish & Submission (End of Week 4)

### Documentation
- [ ] Top-level `README.md`: one-paragraph pitch + run instructions
- [ ] `backend/README.md`: setup, env vars, run, test
- [ ] `frontend/README.md`: setup, run, build
- [ ] `firmware/README.md`: wiring diagram, build, upload, config portal
- [ ] `ml/README.md`: data sources, train, evaluate
- [ ] `prompts/README.md`: how to run Promptfoo
- [ ] Architecture diagram exported as PNG for the README

### Deliverables checklist
- [ ] Source code pushed to Git, latest `main` is demo-ready
- [ ] `SoundSight_Project_Plan_v2.pdf` in `docs/`
- [ ] `SoundSight_Pitch_v2.pdf` in `docs/`
- [ ] ML evaluation report (`ml/REPORT.md` + confusion matrix PNG)
- [ ] Promptfoo run output in `prompts/promptfoo/results/`
- [ ] Ollama `Modelfile` if custom model was used
- [ ] Requirements coverage matrix (from Plan §20) — possibly as a standalone doc for the examiner
- [ ] Demo video (record a clean run as backup for live demo risk)

### Final code cleanup
- [ ] Remove dead code, commented-out blocks, `print` debugging
- [ ] All TODOs in code either resolved or tracked as future work
- [ ] No secrets in Git (double-check `.env` is ignored)
- [ ] Lint + typecheck pass with zero errors

---

## Ongoing / cross-cutting

- [ ] Daily sync between partners (even 10 min) to unblock each other
- [ ] Keep a running `DECISIONS.md` — when we make a design call, write down why
- [ ] Update this checklist as we go — check boxes, add missed items, tick off phases

---

## Handy commands

```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev

# Firmware
cd firmware && pio run -t upload && pio device monitor

# ML
cd ml && python train.py && python evaluate.py

# Promptfoo
cd prompts/promptfoo && promptfoo eval

# Tests
cd backend && pytest
cd frontend && npm test

# Ollama
ollama serve
ollama list
ollama pull llama3.1:8b
```
