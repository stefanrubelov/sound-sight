from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, Event, Rule
from app.dependencies import get_db
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(db: AsyncSession = Depends(get_db)) -> DashboardSummary:
    """Return aggregate counts for the live dashboard header."""
    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = now - timedelta(days=7)

    events_today_result = await db.execute(
        select(func.count()).select_from(Event).where(Event.timestamp >= start_of_today)
    )
    events_today: int = events_today_result.scalar_one()

    events_week_result = await db.execute(
        select(func.count()).select_from(Event).where(Event.timestamp >= start_of_week)
    )
    events_this_week: int = events_week_result.scalar_one()

    top_class_result = await db.execute(
        select(Event.class_name, func.count().label("cnt"))
        .where(Event.timestamp >= start_of_week)
        .group_by(Event.class_name)
        .order_by(func.count().desc())
        .limit(1)
    )
    top_row = top_class_result.first()
    most_active_class = top_row[0] if top_row else None

    device_count_result = await db.execute(select(func.count()).select_from(Device))
    active_device_count: int = device_count_result.scalar_one()

    rule_count_result = await db.execute(select(func.count()).select_from(Rule))
    active_rule_count: int = rule_count_result.scalar_one()

    return DashboardSummary(
        events_today=events_today,
        events_this_week=events_this_week,
        most_active_class=most_active_class,
        active_device_count=active_device_count,
        active_rule_count=active_rule_count,
    )
