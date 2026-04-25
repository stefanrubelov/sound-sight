import logging

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.services.llm.ollama_client import get_chat_model
from app.services.llm.prompt_loader import load_base_system_prompt

log = logging.getLogger(__name__)

SOUND_CLASSES = [
    "fire_alarm",
    "doorbell",
    "glass_breaking",
    "baby_crying",
    "dog_barking",
    "timer_beep",
    "water_running",
]


class SoundProfile(BaseModel):
    enabled_classes: list[str] = Field(
        description=(
            "List of sound class names to enable alerts for. "
            "Choose from: " + ", ".join(SOUND_CLASSES)
        )
    )
    priorities: dict[str, str] = Field(
        description="Priority per enabled class. Values: critical, warn, info"
    )
    quiet_hours_default: dict[str, str] | None = Field(
        default=None,
        description='Default quiet hours as {"start": "HH:MM", "end": "HH:MM"}, or null.',
    )


_parser = PydanticOutputParser(pydantic_object=SoundProfile)

_SYSTEM = """\
{base_system}

## Task
Analyse the user's home description and generate a personalised sound alert profile.
Output valid JSON matching the format instructions exactly.
"""

_HUMAN = """\
{format_instructions}

Available sound classes: {sound_classes}

Home archetype examples:

Example 1 — Single person living alone:
Description: "I live alone in a flat, I work from home, no pets."
Profile: {{"enabled_classes": ["fire_alarm", "glass_breaking", "doorbell", "timer_beep"], "priorities": {{"fire_alarm": "critical", "glass_breaking": "critical", "doorbell": "warn", "timer_beep": "info"}}, "quiet_hours_default": null}}

Example 2 — Family with a baby:
Description: "We have a 6-month-old baby and a golden retriever. Both parents are deaf."
Profile: {{"enabled_classes": ["fire_alarm", "glass_breaking", "baby_crying", "doorbell", "dog_barking", "timer_beep"], "priorities": {{"fire_alarm": "critical", "glass_breaking": "critical", "baby_crying": "critical", "doorbell": "warn", "dog_barking": "info", "timer_beep": "info"}}, "quiet_hours_default": {{"start": "22:00", "end": "07:00"}}}}

Example 3 — Elderly person living alone:
Description: "I am 78 years old with a hearing aid. I live in a house with a garden and a smoke detector."
Profile: {{"enabled_classes": ["fire_alarm", "glass_breaking", "doorbell", "water_running"], "priorities": {{"fire_alarm": "critical", "glass_breaking": "critical", "doorbell": "warn", "water_running": "warn"}}, "quiet_hours_default": {{"start": "21:00", "end": "08:00"}}}}

Now generate a profile for this home:
{home_description}
"""


async def build_profile(home_description: str) -> SoundProfile:
    model = get_chat_model(temperature=0.2, format="json")
    prompt = ChatPromptTemplate.from_messages([("system", _SYSTEM), ("human", _HUMAN)])
    chain = prompt | model | _parser
    return await chain.ainvoke(
        {
            "base_system": load_base_system_prompt(),
            "home_description": home_description,
            "sound_classes": ", ".join(SOUND_CLASSES),
            "format_instructions": _parser.get_format_instructions(),
        }
    )
