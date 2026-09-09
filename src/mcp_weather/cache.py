"""In-memory weather cache for fast local lookups."""

from __future__ import annotations

try:
    from .models import WeatherData
except ImportError:
    from models import WeatherData  # type: ignore[no-redef]

# ── Populated with static defaults at startup ─────────────────────────────────

DEFAULT_ENTRIES: dict[str, WeatherData] = {}


def _seed_defaults() -> dict[str, WeatherData]:
    """Return an empty cache — all lookups go live via Serper + DeepSeek."""
    return {}


def get(city: str) -> WeatherData | None:
    """Look up *city* in the cache (case-insensitive).  Returns None on miss."""
    if not DEFAULT_ENTRIES:
        DEFAULT_ENTRIES.update(_seed_defaults())
    return DEFAULT_ENTRIES.get(city.strip().casefold())
