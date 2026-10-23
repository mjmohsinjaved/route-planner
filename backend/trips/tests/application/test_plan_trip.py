from datetime import timedelta

from django.test import SimpleTestCase

from trips.application.dto import PlanTripCommand
from trips.application.find_routes import FindRoutes
from trips.application.plan_trip import PlanTrip
from trips.domain.entities import Place
from trips.domain.errors import ForecastMissing
from trips.domain.forecast import Reading

from ..fakes import (
    DEPART,
    FakeForecast,
    FakeRoutes,
    InMemoryCache,
    InMemoryTripRepository,
    series,
    straight_route,
    windy_forecast,
)

CHICAGO = Place("Chicago, IL", 41.8832, -87.6324)
DENVER = Place("Denver, CO", 39.7392, -104.9903)


def three_routes(*args):
    return [straight_route(100, 2.0, lon=-100.0), straight_route(110, 2.2, lon=-102.0), straight_route(120, 2.5, lon=-104.0)]


def command(**overrides) -> PlanTripCommand:
    fields = dict(origin=CHICAGO, destination=DENVER, departure=DEPART, load_lb=38_000, interval_mi=25)
    return PlanTripCommand(**{**fields, **overrides})


def planner(forecast=windy_forecast):
    repo = InMemoryTripRepository()
    forecast_port = FakeForecast(forecast)
    use_case = PlanTrip(FindRoutes(FakeRoutes(three_routes), InMemoryCache()), forecast_port, repo)
    return use_case, forecast_port, repo


class PlanTripTests(SimpleTestCase):
    def test_recommends_the_safest_route_and_saves_the_trip(self):
        use_case, _, repo = planner()
        trip = use_case(command())

        self.assertEqual(len(trip.routes), 3)
        self.assertEqual(repo.get(trip.id), trip)
        route_a = trip.routes[0]

        # Route A is the fastest, but its last stretch hits the 47 mph wind.
        # 47 mph + 38,000 lb load -> No Travel, so A must lose to B.
        self.assertGreater(route_a.metrics.no_travel_mi, 0)
        windy = [c for c in route_a.checkpoints if c.risk.level == "No Travel"]
        self.assertEqual(windy[0].risk.reason, "Wind 47.0 mph + 38,000 lb load → No Travel")
        self.assertNotEqual(trip.recommendation.recommended_route_id, "A")
        self.assertFalse(trip.recommendation.unsafe)

    def test_all_checkpoints_of_all_routes_share_one_forecast_lookup(self):
        use_case, forecast, _ = planner()
        use_case(command())
        self.assertEqual(len(forecast.calls), 1)

    def test_lighter_load_changes_the_risk(self):
        use_case, _, _ = planner()
        route_a = use_case(command(load_lb=20_000)).routes[0]
        self.assertEqual(route_a.metrics.no_travel_mi, 0)  # 47 mph alone is Severe, not No Travel
        self.assertGreater(route_a.metrics.severe_mi, 0)

    def test_arrival_is_departure_plus_the_route_duration(self):
        use_case, _, _ = planner()
        route_a = use_case(command()).routes[0]
        self.assertEqual(route_a.arrival, DEPART + timedelta(hours=2))
        self.assertEqual(route_a.checkpoints[-1].checkpoint.eta, route_a.arrival)

    def test_missing_forecast_fails_the_plan_and_saves_nothing(self):
        def with_hole(coords, start, end):
            data = windy_forecast(coords, start, end)
            coord = sorted(data)[0]
            first = min(data[coord])
            data[coord][first] = Reading(None, None, 0.0, 0.0)
            return data

        use_case, _, repo = planner(with_hole)
        with self.assertRaises(ForecastMissing):
            use_case(command())
        self.assertEqual(repo.trips, {})

    def test_every_route_in_no_travel_weather_is_flagged_unsafe(self):
        def gale(coords, start, end):
            first = windy_forecast(coords, start, end)
            return {coord: series(start, len(s), wind=60.0) for coord, s in first.items()}

        use_case, _, _ = planner(gale)
        trip = use_case(command())
        self.assertTrue(trip.recommendation.unsafe)
