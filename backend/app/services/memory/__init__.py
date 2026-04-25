"""Memory services for SoundSight — short-term session + long-term baselines."""

from app.services.memory.baseline import (
    compute_baselines,
    embed_baselines,
    run_baseline_update,
    save_baselines,
)
from app.services.memory.scheduler import get_scheduler, start_scheduler, stop_scheduler
from app.services.memory.session import (
    active_session_count,
    add_ai_message,
    add_user_message,
    clear_session,
    get_messages,
    get_session_memory,
    purge_expired,
)

__all__ = [
    # session
    "get_session_memory",
    "add_user_message",
    "add_ai_message",
    "get_messages",
    "clear_session",
    "purge_expired",
    "active_session_count",
    # baseline
    "compute_baselines",
    "save_baselines",
    "embed_baselines",
    "run_baseline_update",
    # scheduler
    "get_scheduler",
    "start_scheduler",
    "stop_scheduler",
]
