# MCP Weather

An [MCP](https://modelcontextprotocol.io) server that fetches real-time weather for any city — caching popular cities locally and falling back to a live **Serper** web search formatted by **DeepSeek V4 Pro** for everything else.

## Architecture

```
                  ┌──────────────┐
  Claude / client │              │  MCP tool call
  ────────────────▶│  get_weather │──────────────┐
                  │  ("city")    │              │
                  └──────────────┘              │
                                                ▼
                                     ┌────────────────────┐
                                     │  models.WeatherInput│
                                     │  Pydantic validation │
                                     │  strip / reject junk │
                                     └────────┬───────────┘
                                              │
                                   ┌──────────▼──────────┐
                                   │   cache.get(city)    │
                                   │   case-insensitive   │
                                   └──────┬──────┬────────┘
                                     HIT  │      │  MISS
                                          │      │
                                          ▼      ▼
                              ┌──────────┐  ┌────────────────────┐
                              │  return  │  │ providers.lookup   │
                              │  summary │  │ _live(city)        │
                              └──────────┘  └────────┬───────────┘
                                                     │
                                          ┌──────────▼───────────┐
                                          │  Serper Google Search │
                                          │  "weather in {city}"  │
                                          │  (retries on failure) │
                                          └──────────┬───────────┘
                                                     │
                                          ┌──────────▼───────────┐
                                          │  DeepSeek V4 Pro      │
                                          │  JSON extraction      │
                                          │  (OpenRouter)         │
                                          └──────────┬───────────┘
                                                     │
                                          ┌──────────▼───────────┐
                                          │  WeatherData model    │
                                          │  structured response  │
                                          └──────────────────────┘
```

## Quick start

### 1. Install

```bash
cd mcp_weather
uv sync
```

### 2. Set your API keys

Edit `.env` (or export the env vars):

```env
# OpenRouter — used by DeepSeek V4 Pro to format search results
OPENROUTER_API_KEY="sk-or-v1-..."

# Serper — Google Search API (free tier at https://serper.dev)
SERPER_API_KEY="..."
```

### 3. Verify with the smoke test

```bash
uv run python tests/test_imports.py
```

### 4. Wire it into Claude Code

Add this to your `claude_desktop_config.json` or Claude Code MCP config:

```json
{
  "mcpServers": {
    "weather": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/konst/Documents/mcp_start/mcp_weather",
        "python",
        "-m",
        "mcp_weather"
      ]
    }
  }
}
```

Then restart Claude Code — `get_weather` will appear in your tool list.

## Tool reference

### `get_weather(city: str) -> str`

Returns a one-sentence weather summary for the requested city.

| Behaviour | Description |
|---|---|
| **Cache hit** | 12 major cities served instantly from an in-memory cache |
| **Cache miss** | Serper searches Google for current conditions; DeepSeek V4 Pro extracts structured data from the snippets. Retries on transient failures. |
| **Validation** | Pydantic rejects blank, `"none"`, or `"null"` city names before any lookup |

Cached cities: Copenhagen, London, New York, Tokyo, Paris, Sydney, Berlin, Dubai, Moscow, Rio de Janeiro, Mumbai, Cape Town.

## Project layout

```
mcp_weather/
├── .env                        # API keys (git-ignored)
├── .gitignore
├── pyproject.toml              # uv project metadata + dependencies
├── README.md
├── src/
│   └── mcp_weather/
│       ├── __init__.py         # version
│       ├── __main__.py         # python -m entry-point
│       ├── config.py           # .env auto-discovery
│       ├── models.py           # Pydantic input / output schemas
│       ├── cache.py            # in-memory weather cache
│       ├── providers.py        # Serper search + DeepSeek formatting (with retries)
│       └── server.py           # MCP server definition + main()
└── tests/
    └── test_imports.py         # offline smoke test
```

## Dependencies

| Package | Purpose |
|---|---|
| `mcp[cli]` | MCP server framework |
| `pydantic` | Input validation & structured output |
| `httpx` | HTTP client for Serper API (with retries) |
| `openai` | OpenRouter client (DeepSeek V4 Pro) |
| `polars` | Fast DataFrames (available for data tasks) |
| `python-dotenv` | `.env` file loading |

## License

MIT
