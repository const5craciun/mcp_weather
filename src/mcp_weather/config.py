"""Env-var auto-discovery — walk up from this file to find .env."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_LOADED = False


def load_env() -> None:
    """Load .env once.  Idempotent — safe to call in every entry-point.

    Looks for .env in the project root (two levels up from this file) and
    falls back to CWD-based dotenv discovery when running from a different
    layout (e.g. inside a container or installed package).
    """
    global _LOADED
    if _LOADED:
        return
    _LOADED = True

    # Prefer the known project-root location …
    candidate = Path(__file__).resolve().parent.parent.parent / ".env"
    if candidate.exists():
        load_dotenv(candidate)
    else:
        # … otherwise scan CWD / ancestors (pip -e install, etc.)
        load_dotenv()
