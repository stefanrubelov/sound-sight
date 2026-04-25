from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    audio,
    devices,
    events,
    onboarding,
    reports,
    rules,
    settings as settings_router,
    websocket,
)
from app.config import settings
from app.logging import setup_logging
from app.mcp.server import mcp


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    yield


app = FastAPI(title="SoundSight", version="0.1.0", lifespan=lifespan)
app.mount("/mcp", mcp.streamable_http_app())

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


API_PREFIX = "/api"
app.include_router(audio.router, prefix=API_PREFIX)
app.include_router(events.router, prefix=API_PREFIX)
app.include_router(rules.router, prefix=API_PREFIX)
app.include_router(devices.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(onboarding.router, prefix=API_PREFIX)
app.include_router(settings_router.router, prefix=API_PREFIX)
app.include_router(websocket.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
