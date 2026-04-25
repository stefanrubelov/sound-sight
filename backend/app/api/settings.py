import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserProfile
from app.dependencies import get_db
from app.schemas.settings import SettingsRead, SettingsUpdate

log = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


def _profile_to_read(profile: UserProfile) -> SettingsRead:
    enabled = None
    if profile.enabled_classes:
        try:
            enabled = json.loads(profile.enabled_classes)
        except (json.JSONDecodeError, TypeError):
            enabled = None

    quiet = None
    if profile.quiet_hours:
        try:
            quiet = json.loads(profile.quiet_hours)
        except (json.JSONDecodeError, TypeError):
            quiet = None

    return SettingsRead(
        id=profile.id,
        home_description=profile.home_description,
        enabled_classes=enabled,
        quiet_hours=quiet,
        notes=profile.notes,
    )


@router.get("", response_model=SettingsRead)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SettingsRead:
    """Return the current user profile / settings."""
    result = await db.execute(select(UserProfile).limit(1))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile found — complete onboarding first")
    return _profile_to_read(profile)


@router.put("", response_model=SettingsRead)
async def update_settings(
    body: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
) -> SettingsRead:
    """Update mutable fields of the user profile.

    Only fields present in the request body are changed.
    """
    result = await db.execute(select(UserProfile).limit(1))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = UserProfile()
        db.add(profile)

    if body.notes is not None:
        profile.notes = body.notes
    if body.enabled_classes is not None:
        profile.enabled_classes = json.dumps(body.enabled_classes)
    if body.quiet_hours is not None:
        profile.quiet_hours = json.dumps(body.quiet_hours)

    await db.commit()
    await db.refresh(profile)
    log.info("Settings updated: profile_id=%d", profile.id)
    return _profile_to_read(profile)
