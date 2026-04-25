import json
import logging
from datetime import datetime, timedelta, timezone

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Baseline, Event, Rule
from app.services.llm.ollama_client import get_chat_model
from app.services.llm.prompt_loader import load_base_system_prompt

log = logging.getLogger(__name__)

# In-memory cache: {(report_type, date_key): report_text}
_report_cache: dict[tuple[str, str], str] = {}

_HUMAN = """\
Generate a {report_type} sound activity report for a deaf or hard-of-hearing user.

## Events in the past {hours} hours:
{events_summary}

## Active alert rules:
{rules_summary}

## Sound baselines (typical daily activity):
{baselines_summary}

Instructions:
1. Start with a one-sentence overview of the period.
2. Highlight any notable or critical events.
3. Note patterns if present (repeated sounds, sounds during quiet hours).
4. Keep the tone calm and informative — never alarmist.
5. End with one practical observation or reassurance.
Total length: 150–250 words.
"""


async def _query_events(db: AsyncSession, hours: int) -> list[Event]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(Event).where(Event.timestamp >= cutoff).order_by(Event.timestamp.desc()).limit(100)
    )
    return list(result.scalars().all())


async def _query_baselines(db: AsyncSession) -> list[Baseline]:
    result = await db.execute(select(Baseline))
    return list(result.scalars().all())


async def _query_rules(db: AsyncSession) -> list[Rule]:
    result = await db.execute(select(Rule))
    return list(result.scalars().all())


def _fmt_events(events: list[Event]) -> str:
    if not events:
        return "No events recorded in this period."
    lines = []
    for e in events[:20]:
        ts = e.timestamp.strftime("%H:%M") if hasattr(e.timestamp, "strftime") else str(e.timestamp)
        line = (
            f"- {ts}: {e.class_name.replace('_', ' ')} "
            f"({e.confidence:.0%} confidence, {e.duration:.1f}s)"
        )
        if e.llm_summary:
            line += f" — {e.llm_summary}"
        lines.append(line)
    if len(events) > 20:
        lines.append(f"... and {len(events) - 20} more events.")
    return "\n".join(lines)


def _fmt_rules(rules: list[Rule]) -> str:
    if not rules:
        return "No active rules configured."
    return "\n".join(
        f"- {r.trigger.replace('_', ' ')}: {r.priority} priority, {r.alert_type} alert"
        + (f", active {r.time_start}–{r.time_end}" if r.time_start else "")
        for r in rules
    )


def _fmt_baselines(baselines: list[Baseline]) -> str:
    if not baselines:
        return "No baseline data yet — baselines build up after a few days of use."
    lines = []
    for b in baselines:
        try:
            stats = json.loads(b.stats_json)
            lines.append(
                f"- {b.class_name.replace('_', ' ')}: "
                f"avg {stats.get('mean_count_per_day', 0):.1f} events/day"
            )
        except (json.JSONDecodeError, KeyError):
            lines.append(f"- {b.class_name.replace('_', ' ')}: baseline available")
    return "\n".join(lines)


def invalidate_cache(report_type: str | None = None) -> None:
    if report_type is None:
        _report_cache.clear()
    else:
        keys = [k for k in _report_cache if k[0] == report_type]
        for k in keys:
            del _report_cache[k]


async def generate_report(db: AsyncSession, report_type: str = "daily") -> str:
    hours = 24 if report_type == "daily" else 168
    fmt = "%Y-%m-%d" if report_type == "daily" else "%Y-W%W"
    cache_key = (report_type, datetime.now(timezone.utc).strftime(fmt))

    if cache_key in _report_cache:
        log.debug("Returning cached %s report", report_type)
        return _report_cache[cache_key]

    events = await _query_events(db, hours)
    baselines = await _query_baselines(db)
    rules = await _query_rules(db)

    model = get_chat_model(temperature=0.5)
    prompt = ChatPromptTemplate.from_messages(
        [("system", load_base_system_prompt()), ("human", _HUMAN)]
    )
    chain = prompt | model | StrOutputParser()

    try:
        report = await chain.ainvoke(
            {
                "report_type": report_type,
                "hours": hours,
                "events_summary": _fmt_events(events),
                "rules_summary": _fmt_rules(rules),
                "baselines_summary": _fmt_baselines(baselines),
            }
        )
        _report_cache[cache_key] = report.strip()
        return _report_cache[cache_key]
    except Exception as exc:
        log.warning("Report generation failed: %s", exc)
        n = len(events)
        return (
            f"Activity report: {n} sound event{'s' if n != 1 else ''} recorded "
            f"in the past {hours} hours."
        )
