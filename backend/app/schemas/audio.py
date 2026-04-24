from pydantic import BaseModel


class ClassifyResponse(BaseModel):
    event_id: int
    class_name: str
    confidence: float
    severity: str
    led_color: str
    vibration_pattern: str
    device_id: int
