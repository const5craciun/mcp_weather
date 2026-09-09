"""Weather providers — Serper web search + DeepSeek formatting."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field

import httpx
from openai import APIError, OpenAI

try:
    from .models import WeatherData
except ImportError:
    from models import WeatherData  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

# ── Retry configuration ──────────────────────────────────────────────────────

MAX_RETRIES = 2
RETRY_BACKOFF = 1.0  # seconds, multiplied by attempt number
SERPER_TIMEOUT = 10.0  # seconds


# ── Lazy client singleton ────────────────────────────────────────────────────


@dataclass
class _Clients:
    """Lazily-initialised API clients."""

    _openai: OpenAI | None = field(default=None, repr=False, init=False)

    @property
    def serper_key(self) -> str:
        key = os.getenv("SERPER_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "SERPER_API_KEY not set — add it to .env or export it"
            )
        return key

    @property
    def openai(self) -> OpenAI:
        if self._openai is None:
            key = os.getenv("OPENROUTER_API_KEY", "").strip()
            if not key:
                raise RuntimeError(
                    "OPENROUTER_API_KEY not set — add it to .env or export it"
                )
            self._openai = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=key,
            )
        return self._openai


_clients = _Clients()


# ── Serper search ────────────────────────────────────────────────────────────


def _serper_search(query: str) -> str:
    """Call Serper.dev — Google search results as raw text.

    Retries on 5xx / timeouts.  Fails fast on 4xx (bad API key, etc.).
    """
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": _clients.serper_key}

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = httpx.post(
                url,
                json={"q": query, "num": 5},
                headers=headers,
                timeout=SERPER_TIMEOUT,
            )
            resp.raise_for_status()
            return _parse_serper_response(resp.json())

        except httpx.HTTPStatusError as exc:
            if 400 <= exc.response.status_code < 500:
                raise RuntimeError(
                    f"Serper API error {exc.response.status_code}: "
                    f"{exc.response.text[:300]}"
                ) from exc
            last_error = exc
            logger.warning(
                "Serper 5xx (attempt %d/%d): %s",
                attempt + 1, MAX_RETRIES + 1, exc,
            )

        except httpx.TimeoutException as exc:
            last_error = exc
            logger.warning(
                "Serper timeout (attempt %d/%d)",
                attempt + 1, MAX_RETRIES + 1,
            )

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF * (attempt + 1))

    raise RuntimeError(
        f"Serper unavailable after {MAX_RETRIES + 1} attempts"
    ) from last_error


def _parse_serper_response(data: dict) -> str:
    """Extract human-readable text from a Serper JSON response."""
    parts: list[str] = []

    # Direct weather widget — the most relevant data
    answer = data.get("answerBox", {})
    if answer:
        title = answer.get("title", "")
        ans = answer.get("answer", "")
        source = answer.get("source", "")
        if title or ans:
            parts.append(f"[Current Weather — {source}] {title}: {ans}")

    kg = data.get("knowledgeGraph", {})
    if kg:
        title = kg.get("title", "")
        desc = kg.get("description", "")
        if title or desc:
            parts.append(f"[Knowledge Graph] {title}: {desc}")

    for item in data.get("organic", []):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        if title or snippet:
            parts.append(f"{title}: {snippet}")

    return "\n".join(parts) if parts else "(no results)"


# ── DeepSeek formatting ──────────────────────────────────────────────────────

_JSON_RE = re.compile(r"\{[^{}]+\}", re.DOTALL)


def _format_with_deepseek(search_results: str, city: str) -> WeatherData:
    """Ask DeepSeek V4 Pro (via OpenRouter) to extract structured weather."""
    client = _clients.openai

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model="deepseek/deepseek-v4-pro",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Extract the CURRENT weather for {city} from web search results. "
                            f"Return ONLY a JSON object (no markdown) with keys: "
                            f"city, temperature (like 13C), conditions (like cloudy), "
                            f"humidity (like 72%), wind (like 15 km/h), summary. "
                            f"If a field is missing, use null. "
                            f"If temperature is in F, convert to C.\n\n"
                            f"Search results:\n{search_results}"
                        ),
                    },
                ],
                temperature=0.0,
                max_tokens=1024,
            )
            raw = (response.choices[0].message.content or "{}").strip()
            return _parse_weather_json(raw, city)

        except APIError as exc:
            last_error = exc
            logger.warning(
                "OpenRouter error (attempt %d/%d): %s",
                attempt + 1, MAX_RETRIES + 1, exc,
            )

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF * (attempt + 1))

    raise RuntimeError(
        f"OpenRouter unavailable after {MAX_RETRIES + 1} attempts"
    ) from last_error


def _parse_weather_json(raw: str, city: str) -> WeatherData:
    """Parse a (possibly markdown-wrapped) JSON string into WeatherData."""
    m = _JSON_RE.search(raw)
    json_str = m.group(0) if m else raw

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        logger.warning(
            "DeepSeek returned unparseable JSON for %r: %.200s", city, raw
        )
        return WeatherData(
            city=city,
            source="live",
            summary=f"Could not parse weather data for {city}.",
        )

    return WeatherData(
        city=data.get("city", city),
        temperature=data.get("temperature"),
        conditions=data.get("conditions"),
        humidity=data.get("humidity"),
        wind=data.get("wind"),
        source="live",
        summary=data.get(
            "summary", f"{city}: weather currently unavailable"
        ),
    )


# ── Public API ───────────────────────────────────────────────────────────────


def lookup_live(city: str) -> WeatherData:
    """Serper web search → DeepSeek extraction → validated WeatherData."""
    logger.info("live lookup for %r", city)
    snippets = _serper_search(f"current weather in {city}")
    logger.debug("Serper returned %d chars for %r", len(snippets), city)

    result = _format_with_deepseek(snippets, city)
    logger.info("live lookup done for %r: %.120s", city, result.summary)
    return result
