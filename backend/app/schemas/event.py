from datetime import datetime

from pydantic import BaseModel


class EventBase(BaseModel):
    class_name: str
    confidence: float
    duration: float
    device_id: int


class EventCreate(EventBase):
    raw_features: str | None = None


class EventRead(EventBase):
    id: int
    timestamp: datetime
    llm_summary: str | None = None

    model_config = {"from_attributes": True}
