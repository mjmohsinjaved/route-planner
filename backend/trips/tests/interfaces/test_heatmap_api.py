from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from trips.container import build_container, using_container
from trips.domain.errors import ForecastRateLimited
from trips.domain.heatmap_grid import HOURS, corridor_points
from trips.infrastructure.django_trip_repo import DjangoTripRepository

from ..domain.test_heatmap_grid import north_line
from ..fakes import FakeForecast, InMemoryCache, make_trip, windy_forecast


class HeatmapEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        # One route due north along lon -100 from 40 N; windy_forecast blows 47 mph north of 41 N there.
        # The trip is saved through the real repository, so this also covers reading it back from the database.
        self.trip = make_trip([north_line(200)], load_lb=38_000)
        DjangoTripRepository().add(self.trip)
        self.url = f"/api/trips/{self.trip.id}/heatmap/"

    def serve(self, respond=windy_forecast):
        self.forecast = FakeForecast(respond)
        context = using_container(build_container(forecast=self.forecast, cache=InMemoryCache()))
        context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)

    def test_returns_points_hours_and_values(self):
        self.serve()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()

        expected_points = len(corridor_points([north_line(200)]))
        self.assertEqual(len(data["hours"]), HOURS)
        self.assertEqual(len(data["values"]), HOURS)
        self.assertEqual(len(data["points"]), expected_points)
        self.assertTrue(all(len(row) == expected_points for row in data["values"]))
        self.assertTrue(data["hours"][0].endswith(":00:00Z"))

        windy = [i for i, (lat, lon) in enumerate(data["points"]) if lon == -100.0 and lat >= 41.0]
        self.assertTrue(windy)
        for row in data["values"]:
            self.assertTrue(all(row[i] == 4 for i in windy))  # 47 mph + 38,000 lb
            self.assertTrue(all(v == 0 for i, v in enumerate(row) if i not in windy))

    def test_second_request_is_served_from_cache(self):
        self.serve()
        self.client.get(self.url)
        self.assertEqual(len(self.forecast.calls), 1)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(len(self.forecast.calls), 1)

    def test_unknown_trip_is_404(self):
        self.serve()
        res = self.client.get("/api/trips/00000000-0000-0000-0000-000000000000/heatmap/")
        self.assertEqual(res.status_code, 404)
        self.assertIn("detail", res.json())

    def test_weather_rate_limit_is_429_with_retry_after(self):
        def limited(*args):
            raise ForecastRateLimited("Weather service limit reached. Try again in a minute.")

        self.serve(limited)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res["Retry-After"], "60")

    def test_read_endpoints_are_throttled_per_ip(self):
        from trips.interfaces.api import throttling

        self.serve()
        with mock.patch.object(throttling.ReadBurstThrottle, "rate", "1/min", create=True):
            self.assertEqual(self.client.get(self.url).status_code, 200)
            self.assertEqual(self.client.get(self.url).status_code, 429)
