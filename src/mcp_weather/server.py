"""MCP server definition — the weather tool and its wiring."""

from __future__ import annotations

import logging

from mcp.server import MCPServer

# Support both `python -m mcp_weather.server` (relative import) and
# `python server.py` when CWD is inside `src/mcp_weather/` (absolute import).
try:
    from . import cache, models, providers
except ImportError:
    import cache  # type: ignore[no-redef]
    import models  # type: ignore[no-redef]
    import providers  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

mcp = MCPServer("weather")


@mcp.tool()
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Checks a local cache first.  On a cache miss performs a live web search
    via Serper and formats the result with DeepSeek V4 Pro.
    """
    validated = models.WeatherInput(city=city)
    clean = validated.city
    logger.info("get_weather called for %r", clean)

    # 1. Local cache
    cached = cache.get(clean)
    if cached:
        logger.info("cache hit for %r", clean)
        return cached.summary

    # 2. Live lookup
    logger.info("cache miss for %r — falling back to live lookup", clean)
    try:
        data = providers.lookup_live(clean)
        return data.summary
    except RuntimeError as exc:
        logger.warning("configuration error for %r: %s", clean, exc)
        return str(exc)
    except Exception as exc:
        logger.exception("live lookup failed for %r", clean)
        return f"Weather lookup failed for '{clean}': {exc}"


def main() -> None:
    """Bootstrap logging and start the MCP server on stdio."""
    # Load .env — supports both package and direct execution
    try:
        from . import config
    except ImportError:
        import config  # type: ignore[no-redef]

    config.load_env()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=None,  # stderr
    )
    logger.info("starting MCP weather server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
