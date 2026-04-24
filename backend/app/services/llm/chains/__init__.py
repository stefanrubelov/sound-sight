"""LangChain chains — stubs until Phase 6."""


async def summarise_event(class_name: str, event_id: int) -> str:
    """Placeholder: returns a canned summary until the real chain is wired up in Phase 6."""
    return f"Detected {class_name.replace('_', ' ')} (event #{event_id})."
