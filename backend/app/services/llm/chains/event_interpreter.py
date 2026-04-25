import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.services.llm.ollama_client import get_chat_model
from app.services.llm.prompt_loader import load_base_system_prompt

log = logging.getLogger(__name__)

_HUMAN = """\
A new sound event has been detected. Write a 1-2 sentence summary for the user.

Sound: {class_name}
Duration: {duration:.1f} seconds
Location: {device_name} in {room}
Detected at: {timestamp}
{user_context}
Keep the summary clear and factual. Do not mention confidence scores or technical terms.
"""


async def interpret_event(
    class_name: str,
    confidence: float,  # noqa: ARG001 — reserved for future threshold messaging
    duration: float,
    device_name: str = "sensor",
    room: str = "unknown room",
    timestamp: str = "",
    user_notes: str = "",
) -> str:
    class_label = class_name.replace("_", " ").title()
    user_context = f"User notes: {user_notes}\n" if user_notes else ""

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
                "user_context": user_context,
            }
        )
        return result.strip()
    except Exception as exc:
        log.warning("Event interpretation failed: %s", exc)
        return f"{class_label} detected in {room} for {duration:.1f} seconds."
