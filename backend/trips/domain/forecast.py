"""
Which forecast hour describes a moment, and what to do when it is missing.

Pure rules; fetching the forecast is an adapter's job (application/ports.py).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .entities import Checkpoint, Conditions, LatLon
from .errors import ForecastMissing
from .timeutil import floor_hour

COORD_DECIMALS = 1  # ~11 km grid: nearby points share one forecast
MISSING_FORECAST_MESSAGE = "Forecast is not available for part of this trip. Try another departure time."


@dataclass(frozen=True)
class Reading:
    """One hourly stamp for one coordinate. None means the provider had no value."""

    wind_mph: float | None
    gust_mph: float | None
    rain_in: float | None  # total for the hour *before* the stamp
    snow_in: float | None  # total for the hour *before* the stamp


Series = dict[int, Reading]  # epoch seconds (UTC, on the hour) -> reading


def round_coord(lat: float, lon: float) -> LatLon:
    return (round(lat, COORD_DECIMALS), round(lon, COORD_DECIMALS))


def precip_hour(eta: datetime) -> datetime:
    """
    Hour whose rain/snowfall value covers the ETA.

    Rain and snowfall are totals for the *preceding* hour, so the value stamped
    15:00 describes 14:00-15:00. An ETA of 14:20 (or 14:00) therefore reads the
    15:00 value.
    """
    return floor_hour(eta) + timedelta(hours=1)


def wind_hour(eta: datetime) -> datetime:
    """Wind is an instant value, so use the nearest hour (14:29 -> 14:00, 14:30 -> 15:00)."""
    base = floor_hour(eta)
    return base + timedelta(hours=1) if eta.astimezone(timezone.utc) - base >= timedelta(minutes=30) else base


def conditions_at(series: Series, when: datetime) -> Conditions:
    """
    Weather at `when` from one coordinate's hourly series, applying the
    wind-at-nearest-hour and precipitation-from-next-stamp rules above.

    Returns the raw values so risk is classified on the exact forecast value;
    callers round for display. Raises ForecastMissing if the stamp or any of
    wind, rain or snow is missing: a safety tool must not read an unknown as
    calm. Gusts are informational and may be None.
    """
    wind = series.get(int(wind_hour(when).timestamp()))
    precip = series.get(int(precip_hour(when).timestamp()))
    if wind is None or precip is None:
        raise ForecastMissing(MISSING_FORECAST_MESSAGE)
    if wind.wind_mph is None or precip.rain_in is None or precip.snow_in is None:
        raise ForecastMissing(MISSING_FORECAST_MESSAGE)
    return Conditions(
        wind_mph=wind.wind_mph,
        gust_mph=wind.gust_mph,
        rain_in_hr=precip.rain_in,
        snow_in_hr=precip.snow_in,
    )


def checkpoint_window(checkpoints: list[Checkpoint]) -> tuple[datetime, datetime]:
    """First and last forecast stamp needed to cover every checkpoint's ETA."""
    return (
        min(wind_hour(c.eta) for c in checkpoints),
        max(precip_hour(c.eta) for c in checkpoints),
    )
