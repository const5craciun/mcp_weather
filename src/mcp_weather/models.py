"""Pydantic models for input validation and structured output."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class WeatherInput(BaseModel):
    """Validated input for the weather tool."""

    city: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="City name to fetch weather for",
        ),
    ]

    @model_validator(mode="after")
    def _normalize_city(self) -> WeatherInput:
        self.city = self.city.strip()
        if not self.city or self.city.casefold() in {"", "none", "null"}:
            raise ValueError("city must be a non-empty, meaningful string")
        return self


class WeatherData(BaseModel):
    """A single weather data-point returned by a provider."""

    city: str = ""
    temperature: str | None = None
    conditions: str | None = None
    humidity: str | None = None
    wind: str | None = None
    source: str = "cache"  # "cache" or "live"
    summary: str = ""
