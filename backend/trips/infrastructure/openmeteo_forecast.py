"""ForecastPort over the Open-Meteo hourly forecast, with per-coordinate series caching."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Sequence

from ..application.ports import CachePort
from ..domain.entities import LatLon
from ..domain.errors import ForecastRateLimited, ProviderUnavailable
from ..domain.forecast import Reading, Series
from ..domain.timeutil import floor_hour
from . import http

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
VARIABLES = ("wind_speed_10m", "wind_gusts_10m", "rain", "snowfall")
CHUNK_SIZE = 50  # locations per request, keeps the URL short
MAX_PARALLEL = 8  # chunks fetched at the same time; a ~330-point heatmap is 7 chunks, one round
CACHE_SECONDS = 60 * 30
TIMEOUT_SECONDS = 15
RATE_LIMIT_MESSAGE = "Weather service limit reached. Try again in a minute."


def cache_key(coord: LatLon) -> str:
    """One cache entry per coordinate holding its whole fetched hourly series."""
    return f"wx:{coord[0]}:{coord[1]}"


def _value_at(series: list | None, idx: int) -> float | None:
    """Value at idx, or None when the provider has no value for that hour."""
    if not series or idx >= len(series) or series[idx] is None:
        return None
    return float(series[idx])


def _get(params: dict) -> list[dict]:
    """
    GET with a timeout and one retry on network errors or 5xx. A 429 fails at
    once: the allowance resets per minute, so a short pause cannot help and
    would only burn more calls. Always returns a list of locations.
    """
    response = http.get(FORECAST_URL, params=params, timeout=TIMEOUT_SECONDS)
    if response.status_code == 429:
        raise ForecastRateLimited(RATE_LIMIT_MESSAGE)
    data = http.json_or_raise(response)
    return data if isinstance(data, list) else [data]


def _fetch_chunk(chunk: list[LatLon], start: datetime, end: datetime) -> dict[LatLon, Series]:
    """Fetch one batch of coordinates."""
    locations = _get(
        {
            "latitude": ",".join(str(c[0]) for c in chunk),
            "longitude": ",".join(str(c[1]) for c in chunk),
            "hourly": ",".join(VARIABLES),
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "GMT",
            "timeformat": "unixtime",
            "start_hour": start.strftime("%Y-%m-%dT%H:%M"),
            "end_hour": end.strftime("%Y-%m-%dT%H:%M"),
        }
    )
    if len(locations) != len(chunk):
        raise ProviderUnavailable("Weather service returned an unexpected response.")

    out = {}
    for coord, loc in zip(chunk, locations):
        hourly = loc.get("hourly", {})
        out[coord] = {
            int(epoch): Reading(
                wind_mph=_value_at(hourly.get("wind_speed_10m"), idx),
                gust_mph=_value_at(hourly.get("wind_gusts_10m"), idx),
                rain_in=_value_at(hourly.get("rain"), idx),
                snow_in=_value_at(hourly.get("snowfall"), idx),
            )
            for idx, epoch in enumerate(hourly.get("time", []))
        }
    return out


class OpenMeteoForecast:
    def __init__(self, cache: CachePort):
        self.cache = cache

    def hourly(self, coords: Sequence[LatLon], start: datetime, end: datetime) -> dict[LatLon, Series]:
        """
        Hourly readings for each coordinate between `start` and `end` hours (inclusive).

        A coordinate is served from cache when its cached series covers every
        requested hour; the rest are fetched in batches of CHUNK_SIZE, several at a time.
        """
        start, end = floor_hour(start), floor_hour(end)
        stamps = []
        h = start
        while h <= end:
            stamps.append(int(h.timestamp()))
            h += timedelta(hours=1)

        keys = {coord: cache_key(coord) for coord in coords}
        cached = self.cache.get_many(list(keys.values()))
        result: dict[LatLon, Series] = {}
        missing = []
        for coord in coords:
            series = cached.get(keys[coord])
            if series and all(s in series for s in stamps):
                result[coord] = {s: series[s] for s in stamps}
            else:
                missing.append(coord)

        chunks = [missing[i : i + CHUNK_SIZE] for i in range(0, len(missing), CHUNK_SIZE)]
        if not chunks:
            return result

        # Every chunk that succeeds is cached even if another one fails, so a retry
        # only pays for what is still missing instead of the whole grid again.
        failure: Exception | None = None
        to_cache = {}
        with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL, len(chunks))) as pool:
            for future in [pool.submit(_fetch_chunk, chunk, start, end) for chunk in chunks]:
                try:
                    chunk_result = future.result()
                except Exception as exc:  # noqa: BLE001 - re-raised below after caching the rest
                    failure = failure or exc
                    continue
                for coord, series in chunk_result.items():
                    result[coord] = series
                    # Merge with what was cached so a narrow fetch never shrinks a wider series
                    to_cache[keys[coord]] = {**(cached.get(keys[coord]) or {}), **series}
        self.cache.set_many(to_cache, CACHE_SECONDS)
        if failure:
            raise failure
        return result
