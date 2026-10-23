"""In-memory stand-ins for the ports, plus builders shared by the test modules."""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from ..domain.entities import Place, Recommendation, Route, RouteAssessment, RouteMetrics, Trip
from ..domain.errors import TripNotFound
from ..domain.forecast import Reading, Series
from ..domain.geo import METERS_PER_MILE

DEPART = datetime(2026, 10, 21, 8, 0, tzinfo=timezone.utc)


def utc(h: int, m: int = 0) -> datetime:
    return datetime(2026, 10, 21, h, m, tzinfo=timezone.utc)


class InMemoryCache:
    """CachePort that ignores lifetimes."""

    def __init__(self):
        self.items: dict = {}

    def get(self, key):
        return self.items.get(key)

    def set(self, key, value, ttl_seconds):
        self.items[key] = value

    def get_many(self, keys):
        return {k: self.items[k] for k in keys if k in self.items}

    def set_many(self, items, ttl_seconds):
        self.items.update(items)

    def get_or_set(self, key, make, ttl_seconds):
        if key not in self.items:
            self.items[key] = make()
        return self.items[key]


class InMemoryTripRepository:
    def __init__(self):
        self.trips: dict[UUID, Trip] = {}

    def add(self, trip: Trip) -> None:
        self.trips[trip.id] = trip

    def get(self, trip_id: UUID) -> Trip:
        try:
            return self.trips[trip_id]
        except KeyError:
            raise TripNotFound("Not found.") from None


class FakeRoutes:
    """RoutePort that answers with `respond(waypoints, depart_at, vehicle_weight_kg, max_alternatives)`."""

    def __init__(self, respond):
        self.respond = respond
        self.calls: list[tuple] = []

    def calculate(self, waypoints, depart_at, vehicle_weight_kg, max_alternatives):
        self.calls.append((list(waypoints), depart_at, vehicle_weight_kg, max_alternatives))
        result = self.respond(waypoints, depart_at, vehicle_weight_kg, max_alternatives)
        if isinstance(result, Exception):
            raise result
        return result


class FakeForecast:
    """ForecastPort that answers with `respond(coords, start, end) -> {coord: Series}`."""

    def __init__(self, respond):
        self.respond = respond
        self.calls: list[tuple] = []

    def hourly(self, coords, start, end):
        self.calls.append((list(coords), start, end))
        return self.respond(coords, start, end)


class FakeGeocoder:
    def __init__(self, places):
        self.places = places
        self.calls: list[tuple] = []

    def search(self, query, limit):
        self.calls.append((query, limit))
        return self.places


def straight_route(miles: float, hours: float, slow_first_half: bool = False, lon: float = -100.0, rid: str = "") -> Route:
    """A due-north route of `miles` with many points, driven in `hours`."""
    n = 400
    lat_per_mile = 1 / 69.05  # approx. degrees of latitude per mile
    points = [(40.0 + i * miles * lat_per_mile / n, lon) for i in range(n + 1)]
    length_m = miles * METERS_PER_MILE  # official route length; polyline is scaled to it
    total_s = hours * 3600
    if slow_first_half:  # first half takes 75% of the time
        anchors = [(0, 0), (length_m / 2, total_s * 0.75), (length_m, total_s)]
    else:
        anchors = [(0, 0), (length_m, total_s)]
    return Route(id=rid, distance_m=length_m, duration_s=total_s, points=points, time_anchors=anchors)


def hourly_stamps(start: datetime, end: datetime) -> list[datetime]:
    n = int((end - start).total_seconds() // 3600) + 1
    return [start + timedelta(hours=i) for i in range(n)]


def series(start: datetime, hours: int, wind=10.0, rain=0.0, snow=0.0, gust=None) -> Series:
    """{epoch: Reading} for `hours` stamps from `start`. Scalars or per-index lists."""
    pick = lambda v, i: v[i] if isinstance(v, list) else v  # noqa: E731
    out = {}
    for i in range(hours):
        w = pick(wind, i)
        out[int((start + timedelta(hours=i)).timestamp())] = Reading(
            wind_mph=w,
            gust_mph=gust if gust is not None else (None if w is None else w + 5),
            rain_in=pick(rain, i),
            snow_in=pick(snow, i),
        )
    return out


def windy_forecast(coords, start, end) -> dict:
    """Calm everywhere, except 47 mph wind at lon -100 north of latitude 41.0."""
    stamps = hourly_stamps(start, end)
    out = {}
    for lat, lon in coords:
        wind = 47.0 if lon == -100.0 and lat >= 41.0 else 10.0
        out[(lat, lon)] = series(stamps[0], len(stamps), wind=wind, gust=wind + 8)
    return out


def make_trip(geometries, load_lb: int = 38_000, trip_id: UUID | None = None) -> Trip:
    """A minimal saved trip whose routes follow the given polylines (enough for the heatmap)."""
    routes = [
        RouteAssessment(
            id="ABC"[i],
            distance_mi=0,
            duration_min=0,
            arrival=DEPART,
            metrics=RouteMetrics(0, 0, 0, 0.0),
            geometry=list(geometry),
            checkpoints=[],
        )
        for i, geometry in enumerate(geometries)
    ]
    return Trip(
        id=trip_id or uuid4(),
        origin=Place("A", 40.0, -100.0),
        destination=Place("B", 41.8, -100.0),
        departure=DEPART,
        load_lb=load_lb,
        interval_mi=25,
        routes=routes,
        recommendation=Recommendation("A", [r.id for r in routes], "", False),
    )
