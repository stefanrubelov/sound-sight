import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, Event
from app.dependencies import get_db
from app.schemas.event import EventRead

log = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventRead])
async def list_events(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    class_name: str | None = Query(default=None, alias="class"),
    room: str | None = Query(default=None),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
) -> list[EventRead]:
    """Paginated event list with optional filters.

    Filters:
    - ``class`` — exact sound class name
    - ``room``  — device room name (inner-joins Device)
    - ``from``  — ISO timestamp lower bound (inclusive)
    - ``to``    — ISO timestamp upper bound (inclusive)
    """
    stmt = select(Event)

    if room:
        stmt = stmt.join(Device, Event.device_id == Device.id).where(Device.room == room)
    if class_name:
        stmt = stmt.where(Event.class_name == class_name)
    if from_dt:
        stmt = stmt.where(Event.timestamp >= from_dt)
    if to_dt:
        stmt = stmt.where(Event.timestamp <= to_dt)

    stmt = stmt.order_by(Event.timestamp.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return [EventRead.model_validate(e) for e in result.scalars().all()]


@router.post("/{event_id}/explain", response_model=EventRead)
async def explain_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
) -> EventRead:
    """(Re-)generate an LLM explanation for a specific event and persist it."""
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    from app.services.llm.chains import summarise_event

    try:
        summary = await summarise_event(class_name=event.class_name, event_id=event_id)
        event.llm_summary = summary
        await db.commit()
        await db.refresh(event)
    except Exception as exc:
        log.warning("explain_event failed for event %d: %s", event_id, exc)
        raise HTTPException(status_code=503, detail="LLM explanation failed — try again later")

    return EventRead.model_validate(event)
