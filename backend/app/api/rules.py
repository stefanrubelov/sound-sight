import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Rule
from app.dependencies import get_db
from app.schemas.rule import RuleCreate, RuleRead

log = logging.getLogger(__name__)

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("", response_model=RuleRead, status_code=201)
async def create_rule(
    body: RuleCreate,
    db: AsyncSession = Depends(get_db),
) -> RuleRead:
    if body.source_text and not body.trigger:
        try:
            from app.services.llm.chains import parse_rule

            parsed = await parse_rule(body.source_text)
            rule = Rule(
                trigger=parsed.trigger,
                priority=parsed.priority,
                alert_type=parsed.alert_type,
                time_start=parsed.time_start,
                time_end=parsed.time_end,
                source_text=body.source_text,
            )
        except Exception as exc:
            log.warning("Rule parsing failed: %s", exc)
            raise HTTPException(status_code=422, detail=f"Could not parse rule: {exc}")
    else:
        rule = Rule(
            trigger=body.trigger,
            priority=body.priority,
            alert_type=body.alert_type,
            time_start=str(body.time_start) if body.time_start else None,
            time_end=str(body.time_end) if body.time_end else None,
            source_text=body.source_text,
        )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return RuleRead.model_validate(rule)


@router.get("", response_model=list[RuleRead])
async def list_rules(db: AsyncSession = Depends(get_db)) -> list[RuleRead]:
    result = await db.execute(select(Rule).order_by(Rule.created_at.desc()))
    return [RuleRead.model_validate(r) for r in result.scalars().all()]
