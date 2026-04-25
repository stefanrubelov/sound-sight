from pydantic import BaseModel


class DashboardSummary(BaseModel):
    events_today: int
    events_this_week: int
    most_active_class: str | None
    active_device_count: int
    active_rule_count: int
