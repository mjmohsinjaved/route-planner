"""Corridor heatmap for a saved trip: grid, 49 hours of forecast, one risk score per point per hour."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from ..domain.entities import Heatmap, Trip
from ..domain.heatmap_grid import corridor_points, hour_range, score_hours
from ..domain.timeutil import floor_hour
from .ports import CachePort, ForecastPort, TripRepository

CACHE_SECONDS = 60 * 60  # per trip; keeps "hour 0 = now" close to true


class BuildHeatmap:
    def __init__(self, trips: TripRepository, forecast: ForecastPort, cache: CachePort):
        self.trips = trips
        self.forecast = forecast
        self.cache = cache

    def __call__(self, trip_id: UUID, now: datetime | None = None) -> Heatmap:
        """
        Cached per trip and per clock hour, so reopening a trip is instant and
        "+0 h" never labels an hour that has already passed.
        """
        now = now or datetime.now(timezone.utc)
        trip = self.trips.get(trip_id)  # raises TripNotFound before any cache or network work
        key = f"heatmap:{trip.id}:{int(floor_hour(now).timestamp())}"
        return self.cache.get_or_set(key, lambda: self._build(trip, now), CACHE_SECONDS)

    def _build(self, trip: Trip, now: datetime) -> Heatmap:
        points = corridor_points([route.geometry for route in trip.routes])
        hours = hour_range(now)
        data = self.forecast.hourly(points, hours[0], hours[-1] + timedelta(hours=1))  # +1 h for the last precip stamp
        return Heatmap(points=points, hours=hours, values=score_hours(points, hours, data, trip.load_lb))
