import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.services.llm.ollama_client import get_chat_model
from app.services.llm.prompt_loader import load_base_system_prompt

log = logging.getLogger(__name__)

# Confidence threshold below which we fetch KB context for extra grounding
_KB_CONFIDENCE_THRESHOLD = 0.75

_HUMAN = """\
A new sound event has been detected. Write a 1-2 sentence summary for the user.

Sound: {class_name}
Duration: {duration:.1f} seconds
Location: {device_name} in {room}
Detected at: {timestamp}
{user_context}{kb_context}
Keep the summary clear and factual. Do not mention confidence scores or technical terms.
"""


def _fetch_rag_context(class_name: str, confidence: float, room: str) -> tuple[str, str]:
    """Return (home_context_block, kb_context_block) — both may be empty strings."""
    home_ctx = ""
    kb_ctx = ""

    try:
        from app.services.rag.home_knowledge import retrieve_home_context

        raw = retrieve_home_context(f"{class_name} in {room}", k=2)
        if raw:
            home_ctx = f"Home context: {raw}\n"
    except Exception as exc:
        log.debug("Home knowledge retrieval skipped: %s", exc)

    if confidence < _KB_CONFIDENCE_THRESHOLD:
        try:
            from app.services.rag.sound_class_kb import retrieve_class_info

            raw = retrieve_class_info(class_name)
            if raw:
                kb_ctx = f"Sound class reference:\n{raw}\n"
        except Exception as exc:
            log.debug("Sound class KB retrieval skipped: %s", exc)

    return home_ctx, kb_ctx


async def interpret_event(
    class_name: str,
    confidence: float,
    duration: float,
    device_name: str = "sensor",
    room: str = "unknown room",
    timestamp: str = "",
    user_notes: str = "",
) -> str:
    class_label = class_name.replace("_", " ").title()
    user_context = f"User notes: {user_notes}\n" if user_notes else ""

    home_ctx, kb_ctx = _fetch_rag_context(class_name, confidence, room)
    rag_user_context = home_ctx or user_context  # prefer richer home context when available

    model = get_chat_model(temperature=0.3)
    prompt = ChatPromptTemplate.from_messages(
        [("system", load_base_system_prompt()), ("human", _HUMAN)]
    )
    chain = prompt | model | StrOutputParser()

    try:
        result = await chain.ainvoke(
            {
                "class_name": class_label,
                "duration": duration,
                "device_name": device_name,
                "room": room,
                "timestamp": timestamp,
                "user_context": rag_user_context,
                "kb_context": kb_ctx,
            }
        )
        return result.strip()
    except Exception as exc:
        log.warning("Event interpretation failed: %s", exc)
        return f"{class_label} detected in {room} for {duration:.1f} seconds."
