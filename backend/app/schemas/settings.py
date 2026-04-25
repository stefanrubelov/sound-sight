from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    notes: str | None = None
    enabled_classes: list[str] | None = None
    quiet_hours: dict[str, str] | None = None  # {"start": "HH:MM", "end": "HH:MM"} or null


class SettingsRead(BaseModel):
    id: int
    home_description: str | None = None
    enabled_classes: list[str] | None = None
    quiet_hours: dict[str, str] | None = None
    notes: str | None = None
