"""Quick smoke-test — runs without needing API keys."""
from __future__ import annotations

import mcp_weather
from mcp_weather.config import load_env as config_setup
from mcp_weather.models import WeatherInput, WeatherData
from mcp_weather.cache import get as cache_get, DEFAULT_ENTRIES

config_setup()


def test_version() -> None:
    assert mcp_weather.__version__ == "1.0.0"


def test_input_normalize() -> None:
    w = WeatherInput(city="  Tokyo  ")
    assert w.city == "Tokyo"


def test_input_rejects_blank() -> None:
    try:
        WeatherInput(city="   ")
        raise AssertionError("should have raised ValueError")
    except ValueError:
        pass


def test_input_rejects_none() -> None:
    try:
        WeatherInput(city="none")
        raise AssertionError("should have raised ValueError")
    except ValueError:
        pass


def test_cache_always_misses() -> None:
    """No hardcoded defaults — every lookup is a cache miss."""
    assert cache_get("Tokyo") is None
    assert cache_get("London") is None


def test_cache_miss() -> None:
    miss = cache_get("Atlantis")
    assert miss is None


def test_cache_is_empty() -> None:
    count = len([k for k in DEFAULT_ENTRIES if cache_get(k) is not None])
    assert count == 0, f"cache should be empty, got {count} entries"


def test_weather_output_creation() -> None:
    w = WeatherData(
        city="Test City",
        temperature="20°C",
        conditions="sunny",
        source="live",
        summary="Test City: 20°C and sunny.",
    )
    assert w.temperature == "20°C"
    assert w.source == "live"


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_"):
            try:
                func()
                print(f"  ✓ {name}")
            except Exception as e:
                print(f"  ✗ {name}: {e}")
    print("Done.")
