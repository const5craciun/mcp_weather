"""CLI entry point — get weather for any city."""
import sys
from mcp_weather.config import load_env

load_env()

from mcp_weather.server import get_weather

city = sys.argv[1] if len(sys.argv) > 1 else "Tokyo"
print(get_weather(city))
