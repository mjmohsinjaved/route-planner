"""Plan a trip end to end: routes -> checkpoints -> weather -> risk -> recommendation."""
import logging
from datetime import timedelta
from uuid import uuid4

from ..domain.entities import AssessedCheckpoint, Checkpoint, LatLon, Route, RouteAssessment, Trip
from ..domain.forecast import Series, checkpoint_window, conditions_at, round_coord
from ..domain.geo import thin
from ..domain.ranking import recommend, route_metrics
from ..domain.risk import classify
from ..domain.sampling import sample_checkpoints
from .dto import PlanTripCommand
from .find_routes import FindRoutes
from .ports import ForecastPort, TripRepository
from .stopwatch import Stopwatch

logger = logging.getLogger(__name__)


class PlanTrip:
    def __init__(self, find_routes: FindRoutes, forecast: ForecastPort, trips: TripRepository):
        self.find_routes = find_routes
        self.forecast = forecast
        self.trips = trips

    def __call__(self, cmd: PlanTripCommand) -> Trip:
        clock = Stopwatch()
        routes = self.find_routes(cmd.origin, cmd.destination, cmd.departure, cmd.load_lb)
        clock.lap("routes")

        # Checkpoints for every route, then one batched weather lookup for all of them
        per_route = [sample_checkpoints(r, cmd.interval_mi, cmd.departure) for r in routes]
        clock.lap("checkpoints")
        forecast = self._forecast([c for cps in per_route for c in cps])
        clock.lap("weather")

        assessments = [self._assess(route, cps, forecast, cmd) for route, cps in zip(routes, per_route)]
        trip = Trip(
            id=uuid4(),
            origin=cmd.origin,
            destination=cmd.destination,
            departure=cmd.departure,
            load_lb=cmd.load_lb,
            interval_mi=cmd.interval_mi,
            routes=assessments,
            recommendation=recommend(assessments),
        )
        clock.lap("risk+rank")
        self.trips.add(trip)

        logger.info("plan_trip %s -> %s: %s", cmd.origin.name, cmd.destination.name, clock.summary())
        return trip

    def _forecast(self, checkpoints: list[Checkpoint]) -> dict[LatLon, Series]:
        """Hourly forecast for every distinct 0.1 degree cell the checkpoints fall in. One batched lookup."""
        coords = sorted({round_coord(c.lat, c.lon) for c in checkpoints})
        first, last = checkpoint_window(checkpoints)
        return self.forecast.hourly(coords, first, last)

    @staticmethod
    def _assess(route: Route, checkpoints: list[Checkpoint], forecast: dict[LatLon, Series], cmd: PlanTripCommand) -> RouteAssessment:
        assessed = []
        for c in checkpoints:
            w = conditions_at(forecast.get(round_coord(c.lat, c.lon), {}), c.eta)
            risk = classify(w.wind_mph, w.rain_in_hr, w.snow_in_hr, cmd.load_lb)
            assessed.append(AssessedCheckpoint(checkpoint=c, conditions=w, risk=risk))
        return RouteAssessment(
            id=route.id,
            distance_mi=route.distance_mi,
            duration_min=route.duration_min,
            arrival=cmd.departure + timedelta(seconds=route.duration_s),
            metrics=route_metrics(assessed),
            geometry=thin(route.points),
            checkpoints=assessed,
        )
