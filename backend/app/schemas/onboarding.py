from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    home_description: str = Field(min_length=10)


class OnboardingResponse(BaseModel):
    enabled_classes: list[str]
    priorities: dict[str, str]
    quiet_hours_default: dict[str, str] | None = None
    profile_id: int
