from datetime import datetime, time

from pydantic import BaseModel, model_validator


class RuleCreate(BaseModel):
    trigger: str | None = None
    priority: str = "warn"
    alert_type: str = "led"
    time_start: time | None = None
    time_end: time | None = None
    source_text: str | None = None

    @model_validator(mode="after")
    def require_trigger_or_source(self) -> "RuleCreate":
        if not self.trigger and not self.source_text:
            raise ValueError("Provide either 'trigger' or 'source_text'.")
        return self


class RuleRead(BaseModel):
    id: int
    trigger: str
    priority: str
    alert_type: str
    time_start: time | None = None
    time_end: time | None = None
    source_text: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
