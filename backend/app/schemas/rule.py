from datetime import datetime, time

from pydantic import BaseModel


class RuleBase(BaseModel):
    trigger: str
    priority: str = "info"
    alert_type: str = "led"
    time_start: time | None = None
    time_end: time | None = None


class RuleCreate(RuleBase):
    source_text: str | None = None


class RuleRead(RuleBase):
    id: int
    source_text: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
