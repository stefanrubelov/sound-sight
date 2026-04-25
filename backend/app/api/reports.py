import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db

log = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportResponse(BaseModel):
    report_type: str
    content: str


@router.get("/daily", response_model=ReportResponse)
async def daily_report(db: AsyncSession = Depends(get_db)) -> ReportResponse:
    from app.services.llm.agents import generate_report

    content = await generate_report(db, "daily")
    return ReportResponse(report_type="daily", content=content)


@router.get("/weekly", response_model=ReportResponse)
async def weekly_report(db: AsyncSession = Depends(get_db)) -> ReportResponse:
    from app.services.llm.agents import generate_report

    content = await generate_report(db, "weekly")
    return ReportResponse(report_type="weekly", content=content)
