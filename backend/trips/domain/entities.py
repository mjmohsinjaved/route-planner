"""The things the app talks about, as plain dataclasses. No Django, no HTTP, no JSON."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from .geo import METERS_PER_MILE

LatLon = tuple[float, float]


@dataclass(frozen=True)
class Place:
    name: str
    lat: float
    lon: float

    @property
    def latlon(self) -> LatLon:
        return (self.lat, self.lon)


@dataclass(frozen=True)
class Route:
    """A truck route as the routing provider returned it."""

    id: str  # "A", "B", "C" once the set of routes is final
    distance_m: float
    duration_s: float
    points: list[LatLon]
    time_anchors: list[tuple[float, float]]  # (meters from start, seconds from start), ascending

    @property
    def distance_mi(self) -> float:
        return round(self.distance_m / METERS_PER_MILE, 1)

    @property
    def duration_min(self) -> int:
        return round(self.duration_s / 60)


@dataclass(frozen=True)
class Checkpoint:
    """A point on a route. It owns the stretch of road since the previous checkpoint."""

    index: int
    mile: float
    segment_mi: float
    lat: float
    lon: float
    eta: datetime


@dataclass(frozen=True)
class Conditions:
    """Forecast at a checkpoint's ETA, in the raw units of the provider (mph, in/hr)."""

    wind_mph: float
    gust_mph: float | None  # informational; may be missing
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True)
class Risk:
    level: str  # "Low" ... "No Travel"
    level_score: int  # 0 ... 4
    reason: str


@dataclass(frozen=True)
class AssessedCheckpoint:
    checkpoint: Checkpoint
    conditions: Conditions
    risk: Risk

    @property
    def segment_mi(self) -> float:
        return self.checkpoint.segment_mi

    @property
    def level_score(self) -> int:
        return self.risk.level_score


@dataclass(frozen=True)
class RouteMetrics:
    no_travel_mi: float
    severe_mi: float
    high_mi: float
    avg_risk: float


@dataclass(frozen=True)
class RouteAssessment:
    """A route with its checkpoints scored and summed up."""

    id: str
    distance_mi: float
    duration_min: int
    arrival: datetime
    metrics: RouteMetrics
    geometry: list[LatLon]
    checkpoints: list[AssessedCheckpoint]


@dataclass(frozen=True)
class Recommendation:
    recommended_route_id: str
    ranking: list[str]
    reason: str
    unsafe: bool  # every route crosses No Travel weather


@dataclass(frozen=True)
class Trip:
    id: UUID
    origin: Place
    destination: Place
    departure: datetime  # UTC
    load_lb: int
    interval_mi: int
    routes: list[RouteAssessment]
    recommendation: Recommendation


@dataclass(frozen=True)
class Heatmap:
    points: list[LatLon]
    hours: list[datetime]
    values: list[list[int]]  # values[hour][point] = risk score 0-4
