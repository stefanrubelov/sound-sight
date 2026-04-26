"""Dev/demo endpoint: inject a fake classified event without real audio.

Only intended for demo and testing purposes — not part of the production API.
Use `POST /api/dev/inject_event` to simulate any sound class reaching the backend,
which persists an Event row, broadcasts over WebSocket, and returns the same
response shape as /api/audio/classify so the frontend and ESP32 simulator work
identically to a real audio classification.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audio import _write_llm_summary
from app.config import settings
from app.db.models import Event
from app.dependencies import get_db
from app.schemas.audio import ClassifyResponse
from app.services.ws_manager import ws_manager

log = logging.getLogger(__name__)

router = APIRouter(prefix="/dev", tags=["dev"])

VALID_CLASSES = frozenset(
    [
        "fire_alarm",
        "doorbell",
        "glass_breaking",
        "baby_crying",
        "dog_barking",
        "timer_beep",
        "water_running",
        "unknown",
    ]
)


class InjectEventRequest(BaseModel):
    class_name: str = Field(default="doorbell", description="Sound class to simulate")
    confidence: float = Field(default=0.92, ge=0.0, le=1.0)
    device_id: int = Field(default=1)
    duration: float = Field(default=1.0, gt=0.0, description="Duration in seconds")
    llm_summary: str | None = Field(
        default=None,
        description="Optional pre-written summary (skips LLM call)",
    )


@router.post("/inject_event", response_model=ClassifyResponse)
async def inject_event(
    body: InjectEventRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ClassifyResponse:
    """Inject a fake sound event for demo/testing without sending real audio.

    Produces the same side-effects as a real classify call:
    - Persists an Event row in the database.
    - Broadcasts a WebSocket message (frontend updates in real time).
    - Optionally triggers the LLM summary background task.
    """
    class_name = body.class_name if body.class_name in VALID_CLASSES else "unknown"

    severity = settings.class_severity.get(class_name, "none")
    led_color = settings.class_led_color.get(class_name, "#000000")
    vibration_pattern = settings.severity_vibration.get(severity, "none")

    event = Event(
        device_id=body.device_id,
        class_name=class_name,
        confidence=body.confidence,
        duration=body.duration,
        timestamp=datetime.now(timezone.utc),
        llm_summary=body.llm_summary,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    payload = {
        "event_id": event.id,
        "class_name": class_name,
        "confidence": body.confidence,
        "severity": severity,
        "led_color": led_color,
        "vibration_pattern": vibration_pattern,
        "device_id": body.device_id,
        "timestamp": event.timestamp.isoformat(),
    }
    await ws_manager.broadcast(payload)

    if class_name != "unknown" and body.llm_summary is None:
        background_tasks.add_task(_write_llm_summary, event.id, class_name)

    log.info(
        "inject_event: device=%d class=%s confidence=%.2f",
        body.device_id,
        class_name,
        body.confidence,
    )

    return ClassifyResponse(
        event_id=event.id,
        class_name=class_name,
        confidence=body.confidence,
        severity=severity,
        led_color=led_color,
        vibration_pattern=vibration_pattern,
        device_id=body.device_id,
    )
