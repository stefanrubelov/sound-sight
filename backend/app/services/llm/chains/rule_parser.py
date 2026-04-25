import logging
import re
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator

from app.services.llm.ollama_client import get_chat_model
from app.services.llm.prompt_loader import load_base_system_prompt

log = logging.getLogger(__name__)

VALID_CLASSES = frozenset(
    [
        "fire_alarm",
        "doorbell",
        "glass_breaking",
        "baby_crying",
        "dog_barking",
        "timer_beep",
        "water_running",
        "unknown",
    ]
)
VALID_PRIORITIES = frozenset(["critical", "warn", "info", "none"])
VALID_ALERT_TYPES = frozenset(["led", "vibration", "both", "none"])


class ParsedRule(BaseModel):
    trigger: str = Field(
        description=(
            "Sound class to trigger on. One of: fire_alarm, doorbell, glass_breaking, "
            "baby_crying, dog_barking, timer_beep, water_running, unknown"
        )
    )
    priority: str = Field(
        default="warn",
        description="Alert priority: critical, warn, info, or none",
    )
    alert_type: str = Field(
        default="led",
        description="Alert method: led, vibration, both, or none",
    )
    time_start: str | None = Field(
        default=None,
        description="Start of active window as HH:MM (24-hour). Null if no time restriction.",
    )
    time_end: str | None = Field(
        default=None,
        description="End of active window as HH:MM (24-hour). Null if no time restriction.",
    )

    @field_validator("trigger")
    @classmethod
    def validate_trigger(cls, v: str) -> str:
        v = v.lower().strip().replace(" ", "_").replace("-", "_")
        return v if v in VALID_CLASSES else "unknown"

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        v = v.lower().strip()
        return v if v in VALID_PRIORITIES else "warn"

    @field_validator("alert_type")
    @classmethod
    def validate_alert_type(cls, v: str) -> str:
        v = v.lower().strip()
        return v if v in VALID_ALERT_TYPES else "led"

    @field_validator("time_start", "time_end", mode="before")
    @classmethod
    def validate_time(cls, v: Any) -> str | None:
        if v is None or str(v).lower() in ("null", "none", "n/a", ""):
            return None
        s = str(v).strip()
        if re.match(r"^\d{1,2}:\d{2}$", s):
            h, m = s.split(":")
            return f"{int(h):02d}:{m}"
        return None


_parser = PydanticOutputParser(pydantic_object=ParsedRule)

_SYSTEM = """\
{base_system}

## Task
Parse the user's natural-language alert rule into a structured JSON rule.
Output valid JSON matching the format instructions exactly — nothing else.
"""

_HUMAN = """\
{format_instructions}

Sound classes: fire_alarm, doorbell, glass_breaking, baby_crying, dog_barking, timer_beep, water_running, unknown

Priority mapping:
- urgent / critical / emergency → critical
- warn / alert / notify → warn
- info / low / quiet → info
- silence / disable / ignore → none

Alert type mapping:
- flash / light / LED → led
- vibrate / buzz / shake → vibration
- both / all → both
- nothing / silent / off → none

Time of day shortcuts:
- "at night" / "overnight" → time_start=22:00, time_end=07:00
- "during the day" / "daytime" → time_start=07:00, time_end=22:00
- "after midnight" → time_start=00:00, time_end=06:00
- "in the morning" → time_start=06:00, time_end=12:00
- no time mentioned → time_start=null, time_end=null

Examples:
Input: "Alert me if the fire alarm goes off at night"
Output: {{"trigger": "fire_alarm", "priority": "critical", "alert_type": "both", "time_start": "22:00", "time_end": "07:00"}}

Input: "Vibrate when the doorbell rings"
Output: {{"trigger": "doorbell", "priority": "warn", "alert_type": "vibration", "time_start": null, "time_end": null}}

Input: "Flash the LED for any dog barking during the day"
Output: {{"trigger": "dog_barking", "priority": "info", "alert_type": "led", "time_start": "07:00", "time_end": "22:00"}}

Input: "Notify me urgently if glass breaks any time"
Output: {{"trigger": "glass_breaking", "priority": "critical", "alert_type": "both", "time_start": null, "time_end": null}}

Input: "Ignore water running sounds"
Output: {{"trigger": "water_running", "priority": "none", "alert_type": "none", "time_start": null, "time_end": null}}

Now parse this rule:
{rule_text}
"""


async def parse_rule(nl_text: str) -> ParsedRule:
    model = get_chat_model(temperature=0, format="json")
    prompt = ChatPromptTemplate.from_messages([("system", _SYSTEM), ("human", _HUMAN)])
    chain = prompt | model | _parser
    return await chain.ainvoke(
        {
            "base_system": load_base_system_prompt(),
            "rule_text": nl_text,
            "format_instructions": _parser.get_format_instructions(),
        }
    )
