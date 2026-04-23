from datetime import datetime

from pydantic import BaseModel


class DeviceBase(BaseModel):
    name: str
    room: str


class DeviceCreate(DeviceBase):
    pass


class DeviceRead(DeviceBase):
    id: int
    registered_at: datetime
    last_seen: datetime | None = None

    model_config = {"from_attributes": True}
