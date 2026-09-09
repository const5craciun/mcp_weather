"""CLI entry point — `python -m mcp_weather` or `uv run mcp-weather`."""

from __future__ import annotations

# Load .env — supports both package and direct execution
try:
    from . import config
except ImportError:
    import config  # type: ignore[no-redef]

config.load_env()

try:
    from .server import main
except ImportError:
    from server import main  # type: ignore[no-redef]

main()
