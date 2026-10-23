"""
What the use cases need from the outside world, as interfaces (structural
Protocols). Adapters in infrastructure/ implement them; tests pass fakes.

Adapters raise the errors in domain/errors.py, never the errors of the HTTP
library they use.
"""
from datetime import datetime
from typing import Callable, Protocol, Sequence
from uuid import UUID

from ..domain.entities import LatLon, Place, Route, Trip
from ..domain.forecast import Series


class RoutePort(Protocol):
    def calculate(
        self, waypoints: Sequence[LatLon], depart_at: datetime, vehicle_weight_kg: int, max_alternatives: int
    ) -> list[Route]:
        """Truck routes through the waypoints (origin, any via-points, destination). Ids are blank."""


class ForecastPort(Protocol):
    def hourly(self, coords: Sequence[LatLon], start: datetime, end: datetime) -> dict[LatLon, Series]:
        """Hourly readings for each coordinate from `start` to `end` hours, inclusive."""


class GeocoderPort(Protocol):
    def search(self, query: str, limit: int) -> list[Place]: ...


class TripRepository(Protocol):
    def add(self, trip: Trip) -> None: ...

    def get(self, trip_id: UUID) -> Trip:
        """Raises TripNotFound."""


class CachePort(Protocol):
    def get(self, key: str): ...

    def set(self, key: str, value, ttl_seconds: int) -> None: ...

    def get_many(self, keys: Sequence[str]) -> dict: ...

    def set_many(self, items: dict, ttl_seconds: int) -> None: ...

    def get_or_set(self, key: str, make: Callable[[], object], ttl_seconds: int): ...
