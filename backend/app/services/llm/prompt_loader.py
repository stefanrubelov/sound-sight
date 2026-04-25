from pathlib import Path

_BASE_PROMPT_PATH = Path(__file__).parents[4] / "prompts" / "base_system.md"

_FALLBACK = (
    "You are SoundSight, a home sound-detection assistant for deaf and hard-of-hearing users."
)


def load_base_system_prompt() -> str:
    try:
        return _BASE_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return _FALLBACK


def merge_with_role(role_prompt: str) -> str:
    return f"{load_base_system_prompt()}\n\n{role_prompt}"
