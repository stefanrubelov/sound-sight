import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserProfile
from app.dependencies import get_db
from app.schemas.onboarding import OnboardingRequest, OnboardingResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/profile", response_model=OnboardingResponse)
async def create_profile(
    body: OnboardingRequest,
    db: AsyncSession = Depends(get_db),
) -> OnboardingResponse:
    from app.services.llm.chains import build_profile

    profile_data = await build_profile(body.home_description)

    result = await db.execute(select(UserProfile).limit(1))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = UserProfile()
        db.add(profile)

    profile.home_description = body.home_description
    profile.enabled_classes = json.dumps(profile_data.enabled_classes)
    if profile_data.quiet_hours_default:
        profile.quiet_hours = json.dumps(profile_data.quiet_hours_default)

    await db.commit()
    await db.refresh(profile)

    # Re-index home knowledge in RAG whenever the profile changes
    try:
        from app.services.rag.home_knowledge import index_profile

        index_profile(
            profile_id=profile.id,
            home_description=profile.home_description,
            notes=profile.notes,
        )
    except Exception as exc:
        log.warning("RAG home knowledge indexing failed for profile %d: %s", profile.id, exc)

    return OnboardingResponse(
        enabled_classes=profile_data.enabled_classes,
        priorities=profile_data.priorities,
        quiet_hours_default=profile_data.quiet_hours_default,
        profile_id=profile.id,
    )
