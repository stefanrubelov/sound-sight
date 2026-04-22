"""SoundSight backend entry point. Placeholder — real routes come in Phase 1."""
from fastapi import FastAPI

app = FastAPI(title="SoundSight", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
