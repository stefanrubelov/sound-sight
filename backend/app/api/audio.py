import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Device, Event
from app.dependencies import get_db
from app.schemas.audio import ClassifyResponse
from app.services.ml.classifier import get_classifier
from app.services.ws_manager import ws_manager

log = logging.getLogger(__name__)

router = APIRouter(prefix="/audio", tags=["audio"])

# Duration is estimated from the PCM byte length (16-bit mono at SAMPLE_RATE)
_SAMPLE_RATE = 16000
_BYTES_PER_SAMPLE = 2  # int16


def _estimate_duration(pcm_bytes: bytes) -> float:
    n_samples = len(pcm_bytes) // _BYTES_PER_SAMPLE
    return max(n_samples / _SAMPLE_RATE, 0.0)


def _resolve_severity(class_name: str) -> str:
    return settings.class_severity.get(class_name, "none")


def _resolve_led_color(class_name: str) -> str:
    return settings.class_led_color.get(class_name, "#000000")


def _resolve_vibration(severity: str) -> str:
    return settings.severity_vibration.get(severity, "none")


async def _write_llm_summary(event_id: int, class_name: str) -> None:
    """Background task: generate LLM summary + anomaly check in a fresh DB session."""
    from app.db.session import AsyncSessionLocal
    from app.services.llm.agents import check_and_narrate_anomaly
    from app.services.llm.chains import summarise_event

    try:
        summary = await asyncio.wait_for(
            summarise_event(class_name=class_name, event_id=event_id),
            timeout=30.0,
        )
    except Exception as exc:
        log.warning("LLM summary failed for event %d: %s", event_id, exc)
        summary = None

    try:
        async with AsyncSessionLocal() as db:
            event = await db.get(Event, event_id)
            if event is None:
                return

            room = "unknown room"
            if event.device_id:
                device = await db.get(Device, event.device_id)
                if device:
                    room = device.room

            anomaly = await asyncio.wait_for(
                check_and_narrate_anomaly(event, room, db),
                timeout=30.0,
            )

            if anomaly:
                event.llm_summary = (
                    f"{summary}\n\n[Anomaly] {anomaly}" if summary else f"[Anomaly] {anomaly}"
                )
            elif summary:
                event.llm_summary = summary

            if event.llm_summary:
                await db.commit()
                log.debug("LLM summary written for event %d", event_id)
    except Exception as exc:
        log.warning("Post-event LLM task failed for event %d: %s", event_id, exc)


@router.post("/classify", response_model=ClassifyResponse)
async def classify_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    device_id: int = 0,
    db: AsyncSession = Depends(get_db),
) -> ClassifyResponse:
    """Accept raw 16-bit signed PCM bytes and return a classification result.

    The ESP32 sends audio as `application/octet-stream`. Pass `?device_id=<id>`
    in the query string (registered via `POST /api/devices/register`).
    """
    pcm_bytes = await request.body()
    if not pcm_bytes:
        raise HTTPException(status_code=422, detail="Request body must contain PCM audio bytes")

    # --- Run classifier ---
    clf = get_classifier()
    if clf is None:
        # Model not yet trained — return unknown with low severity so the ESP32
        # still gets a valid response and can continue operating.
        class_name = "unknown"
        confidence = 0.0
        all_scores: dict[str, float] = {}
    else:
        result = clf.predict(pcm_bytes)
        class_name = result.class_name
        confidence = result.confidence
        all_scores = result.all_scores

    severity = _resolve_severity(class_name)
    led_color = _resolve_led_color(class_name)
    vibration_pattern = _resolve_vibration(severity)
    duration = _estimate_duration(pcm_bytes)

    # --- Persist event ---
    event = Event(
        device_id=device_id,
        class_name=class_name,
        confidence=confidence,
        duration=duration,
        raw_features=json.dumps(all_scores) if all_scores else None,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # --- Update device last_seen ---
    if device_id:
        device = await db.get(Device, device_id)
        if device:
            device.last_seen = datetime.now(timezone.utc)
            await db.commit()

    # --- Broadcast over WebSocket ---
    payload = {
        "event_id": event.id,
        "class_name": class_name,
        "confidence": confidence,
        "severity": severity,
        "led_color": led_color,
        "vibration_pattern": vibration_pattern,
        "device_id": device_id,
        "timestamp": event.timestamp.isoformat(),
    }
    await ws_manager.broadcast(payload)

    # --- Async LLM summary (don't block the ESP32) ---
    if class_name != "unknown":
        background_tasks.add_task(_write_llm_summary, event.id, class_name)

    log.info(
        "classify: device=%d class=%s confidence=%.3f severity=%s",
        device_id,
        class_name,
        confidence,
        severity,
    )

    return ClassifyResponse(
        event_id=event.id,
        class_name=class_name,
        confidence=confidence,
        severity=severity,
        led_color=led_color,
        vibration_pattern=vibration_pattern,
        device_id=device_id,
    )
