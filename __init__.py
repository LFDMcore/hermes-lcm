"""Hermes LCM Plugin — Lossless Context Management.

Replaces the built-in ContextCompressor with a DAG-based context engine
that persists every message and provides structured retrieval tools.

Based on the LCM paper by Ehrlich & Blackman (Voltropy PBC, Feb 2026).
"""

import logging
import os

logger = logging.getLogger(__name__)


def _env_flag_enabled(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def register(ctx):
    """Plugin entry point — register the LCM context engine."""
    from .config import LCMConfig
    from .engine import LCMEngine

    config = LCMConfig.from_env()

    # Resolve hermes_home for profile-scoped storage
    hermes_home = ""
    try:
        from hermes_cli.config import get_hermes_home
        hermes_home = str(get_hermes_home())
    except Exception:
        hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))

    # Kanban workers are session-filtered as read-only. Do not bootstrap the
    # shared database before their session filter gets a chance to apply.
    eager_storage_bootstrap = os.environ.get("HERMES_SESSION_SOURCE", "").strip() != "kanban"
    engine = LCMEngine(
        config=config,
        hermes_home=hermes_home,
        eager_storage_bootstrap=eager_storage_bootstrap,
    )

    # Register as the context engine (replaces ContextCompressor)
    ctx.register_context_engine(engine)

    register_command = getattr(ctx, "register_command", None)
    slash_enabled = _env_flag_enabled("LCM_ENABLE_SLASH_COMMAND", default=False)
    if callable(register_command) and slash_enabled:
        from .command import handle_lcm_command

        register_command(
            "lcm",
            lambda raw_args: handle_lcm_command(raw_args, engine),
            description="LCM status and diagnostics",
        )
    elif callable(register_command):
        logger.info("LCM slash command registration disabled (set LCM_ENABLE_SLASH_COMMAND=1 to enable /lcm)")
    else:
        logger.info("LCM slash command registration unavailable on this Hermes host; continuing without /lcm")

    logger.info("LCM plugin loaded — lossless context management active")
