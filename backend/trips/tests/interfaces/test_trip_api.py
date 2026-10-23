"""End-to-end tests of the trip endpoints: real views, use cases and database; fake routing and weather."""
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from trips.container import build_container, using_container
from trips.domain.errors import ForecastRateLimited, NoRouteFound, ProviderTimeout, ProviderUnavailable
from trips.domain.forecast import Reading
from trips.infrastructure.openmeteo_forecast import RATE_LIMIT_MESSAGE
from trips.interfaces.api import throttling
from trips.models import TripPlan

from ..application.test_plan_trip import three_routes
from ..fakes import FakeForecast, FakeRoutes, InMemoryCache, windy_forecast

CHICAGO = {"name": "Chicago, IL", "lat": 41.8832, "lon": -87.6324}
DENVER = {"name": "Denver, CO", "lat": 39.7392, "lon": -104.9903}


class TripApiTests(TestCase):
    def setUp(self):
        cache.clear()  # throttle counters live in Django's cache
        self.body = {
            "origin": CHICAGO,
            "destination": DENVER,
            "departure": (timezone.now() + timedelta(hours=1)).isoformat(),
            "load_lb": 38_000,
            "interval_mi": 25,
        }

    def serve(self, routes=three_routes, forecast=windy_forecast):
        container = build_container(routes=FakeRoutes(routes), forecast=FakeForecast(forecast), cache=InMemoryCache())
        context = using_container(container)
        context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)

    def post(self, body=None):
        return self.client.post("/api/trips/", body or self.body, content_type="application/json")

    def test_plans_trip_and_recommends_safest_route(self):
        self.serve()
        res = self.post()
        self.assertEqual(res.status_code, 201, res.content)
        data = res.json()

        self.assertEqual(len(data["routes"]), 3)
        self.assertEqual(TripPlan.objects.count(), 1)
        route_a, route_b, _ = data["routes"]

        # Route A is the fastest, but its last stretch hits the 47 mph wind.
        # 47 mph + 38,000 lb load -> No Travel, so A must lose to B.
        self.assertGreater(route_a["no_travel_mi"], 0)
        windy = [c for c in route_a["checkpoints"] if c["level"] == "No Travel"]
        self.assertEqual(windy[0]["reason"], "Wind 47.0 mph + 38,000 lb load → No Travel")
        self.assertNotEqual(data["recommended_route_id"], "A")
        self.assertFalse(data["unsafe"])

        cp = route_b["checkpoints"][1]
        for key in ("mile", "lat", "lon", "eta", "wind_mph", "gust_mph", "rain_in_hr", "snow_in_hr", "level", "reason"):
            self.assertIn(key, cp)
        self.assertTrue(cp["eta"].endswith("Z"))
        self.assertIsInstance(route_a["geometry"], str)

        # The saved trip can be reopened by id
        again = self.client.get(f"/api/trips/{data['id']}/")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json(), data)

    def test_lighter_load_changes_the_risk(self):
        self.serve()
        route_a = self.post({**self.body, "load_lb": 20_000}).json()["routes"][0]
        self.assertEqual(route_a["no_travel_mi"], 0)  # 47 mph alone is Severe, not No Travel
        self.assertGreater(route_a["severe_mi"], 0)

    def test_unknown_trip_is_404_with_detail(self):
        self.serve()
        res = self.client.get("/api/trips/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json(), {"detail": "Not found."})

    def test_rejects_same_origin_and_destination(self):
        res = self.post({**self.body, "destination": CHICAGO})
        self.assertEqual(res.status_code, 400)
        self.assertIn("destination", res.json())
        self.assertEqual(res.json()["detail"], "Destination must be different from the origin.")

    def test_rejects_past_departure(self):
        res = self.post({**self.body, "departure": (timezone.now() - timedelta(days=1)).isoformat()})
        self.assertEqual(res.status_code, 400)
        self.assertIn("departure", res.json())
        self.assertEqual(res.json()["detail"], "Departure can't be in the past.")

    def test_rejects_departure_beyond_forecast(self):
        res = self.post({**self.body, "departure": (timezone.now() + timedelta(days=20)).isoformat()})
        self.assertEqual(res.status_code, 400)
        self.assertIn("days ahead", res.json()["detail"])

    def test_rejects_bad_interval_and_load(self):
        res = self.post({**self.body, "interval_mi": 30, "load_lb": 0})
        self.assertEqual(res.status_code, 400)
        self.assertIn("interval_mi", res.json())
        self.assertIn("load_lb", res.json())
        self.assertIsInstance(res.json()["detail"], str)  # every 400 carries one sentence for the UI

    def test_malformed_json_has_detail(self):
        res = self.client.post("/api/trips/", "{not json", content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("detail", res.json())

    def test_missing_forecast_returns_502_not_a_calm_route(self):
        def with_hole(coords, start, end):
            data = windy_forecast(coords, start, end)
            coord = sorted(data)[0]
            data[coord][min(data[coord])] = Reading(None, None, 0.0, 0.0)
            return data

        self.serve(forecast=with_hole)
        res = self.post()
        self.assertEqual(res.status_code, 502)
        self.assertEqual(res.json()["detail"], "Forecast is not available for part of this trip. Try another departure time.")
        self.assertEqual(TripPlan.objects.count(), 0)

    def test_plan_endpoint_is_throttled_per_ip(self):
        self.serve()
        with mock.patch.object(throttling.PlanBurstThrottle, "rate", "2/min", create=True):
            self.assertEqual(self.post().status_code, 201)
            self.assertEqual(self.post().status_code, 201)
            res = self.post()
        self.assertEqual(res.status_code, 429)
        self.assertIn("detail", res.json())
        self.assertTrue(res.has_header("Retry-After"))

    def test_no_route_returns_422(self):
        self.serve(routes=lambda *a: [])
        res = self.post()
        self.assertEqual(res.status_code, 422)
        self.assertEqual(res.json()["detail"], NoRouteFound("No truck route found between these places.").args[0])

    def test_service_failure_returns_502(self):
        self.serve(routes=lambda *a: ProviderUnavailable())
        res = self.post()
        self.assertEqual(res.status_code, 502)
        self.assertEqual(res.json()["detail"], "A routing or weather service failed. Try again.")

    def test_timeout_returns_504(self):
        self.serve(routes=lambda *a: ProviderTimeout())
        res = self.post()
        self.assertEqual(res.status_code, 504)
        self.assertEqual(res.json()["detail"], "A routing or weather service took too long. Try again.")

    def test_weather_rate_limit_returns_429_with_retry_after(self):
        def limited(*args):
            raise ForecastRateLimited(RATE_LIMIT_MESSAGE)

        self.serve(forecast=limited)
        res = self.post()
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.json()["detail"], RATE_LIMIT_MESSAGE)
        self.assertEqual(res["Retry-After"], "60")
