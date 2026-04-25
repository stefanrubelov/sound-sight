import json
import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Baseline, Event
from app.services.llm.ollama_client import get_chat_model
from app.services.llm.prompt_loader import load_base_system_prompt

log = logging.getLogger(__name__)

_SIGMA_THRESHOLD = 3.0

_HUMAN = """\
A sound event has been flagged as anomalous. Write a brief (2–3 sentence) explanation for the user.

Sound: {class_name}
Duration: {duration:.1f} seconds (typical: {mean_duration:.1f}s ± {std_duration:.1f}s)
Deviation: {sigma:.1f} standard deviations above normal
Room: {room}
Time: {timestamp}

Explain what this anomaly might mean without unnecessary alarm.
Suggest one practical action if appropriate.
"""


async def check_and_narrate_anomaly(
    event: Event,
    room: str,
    db: AsyncSession,
) -> str | None:
    """Return a narration if event duration is more than 3σ above baseline, else None."""
    result = await db.execute(select(Baseline).where(Baseline.class_name == event.class_name))
    baseline = result.scalar_one_or_none()
    if baseline is None:
        return None

    try:
        stats = json.loads(baseline.stats_json)
        mean_dur = float(stats.get("mean_duration", 0))
        std_dur = float(stats.get("std_duration", 1))
    except (json.JSONDecodeError, KeyError, ValueError):
        return None

    if std_dur < 0.01:
        return None

    sigma = (event.duration - mean_dur) / std_dur
    if sigma <= _SIGMA_THRESHOLD:
        return None

    log.info(
        "Anomaly: event %d is %.1fσ above baseline for %s",
        event.id,
        sigma,
        event.class_name,
    )

    model = get_chat_model(temperature=0.4)
    prompt = ChatPromptTemplate.from_messages(
        [("system", load_base_system_prompt()), ("human", _HUMAN)]
    )
    chain = prompt | model | StrOutputParser()

    try:
        narration = await chain.ainvoke(
            {
                "class_name": event.class_name.replace("_", " ").title(),
                "duration": event.duration,
                "mean_duration": mean_dur,
                "std_duration": std_dur,
                "sigma": sigma,
                "room": room,
                "timestamp": event.timestamp.isoformat(),
            }
        )
        return narration.strip()
    except Exception as exc:
        log.warning("Anomaly narration failed: %s", exc)
        return (
            f"Unusual {event.class_name.replace('_', ' ')} detected: "
            f"{event.duration:.1f}s duration (expected ~{mean_dur:.1f}s)."
        )
