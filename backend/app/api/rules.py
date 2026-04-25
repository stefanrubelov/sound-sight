import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Rule
from app.dependencies import get_db
from app.schemas.rule import RuleCreate, RuleRead

log = logging.getLogger(__name__)

router = APIRouter(prefix="/rules", tags=["rules"])


def _log_to_session(session_id: str | None, user_text: str, ai_text: str) -> None:
    """Persist the NL rule exchange to short-term session memory if a session id is given."""
    if not session_id:
        return
    try:
        from app.services.memory.session import add_ai_message, add_user_message

        add_user_message(session_id, user_text)
        add_ai_message(session_id, ai_text)
    except Exception as exc:
        log.debug("Session memory write skipped: %s", exc)


@router.post("", response_model=RuleRead, status_code=201)
async def create_rule(
    body: RuleCreate,
    db: AsyncSession = Depends(get_db),
    x_session_id: str | None = Header(default=None),
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
            _log_to_session(
                x_session_id,
                user_text=body.source_text,
                ai_text=(
                    f"Rule created: {parsed.trigger}, {parsed.priority} priority, "
                    f"{parsed.alert_type} alert"
                    + (
                        f", active {parsed.time_start}–{parsed.time_end}"
                        if parsed.time_start
                        else ""
                    )
                    + "."
                ),
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
