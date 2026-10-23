from datetime import timedelta
from uuid import uuid4

from django.test import SimpleTestCase

from trips.application.build_heatmap import BuildHeatmap
from trips.domain.errors import TripNotFound
from trips.domain.heatmap_grid import HOURS, corridor_points

from ..domain.test_heatmap_grid import north_line
from ..fakes import FakeForecast, InMemoryCache, InMemoryTripRepository, make_trip, utc, windy_forecast


def setup(load_lb=38_000):
    trips = InMemoryTripRepository()
    trip = make_trip([north_line(200)], load_lb=load_lb)
    trips.add(trip)
    forecast = FakeForecast(windy_forecast)
    return BuildHeatmap(trips, forecast, InMemoryCache()), forecast, trip


class BuildHeatmapTests(SimpleTestCase):
    def test_returns_points_hours_and_values(self):
        use_case, _, trip = setup()
        heatmap = use_case(trip.id, now=utc(14, 35))

        expected_points = len(corridor_points([north_line(200)]))
        self.assertEqual(len(heatmap.hours), HOURS)
        self.assertEqual(len(heatmap.values), HOURS)
        self.assertEqual(len(heatmap.points), expected_points)
        self.assertTrue(all(len(row) == expected_points for row in heatmap.values))
        self.assertEqual(heatmap.hours[0], utc(14))

        windy = [i for i, (lat, lon) in enumerate(heatmap.points) if lon == -100.0 and lat >= 41.0]
        self.assertTrue(windy)
        for row in heatmap.values:
            self.assertTrue(all(row[i] == 4 for i in windy))  # 47 mph + 38,000 lb
            self.assertTrue(all(v == 0 for i, v in enumerate(row) if i not in windy))

    def test_load_decides_the_score(self):
        use_case, _, trip = setup(load_lb=20_000)
        heatmap = use_case(trip.id, now=utc(14))
        self.assertEqual(max(max(row) for row in heatmap.values), 3)  # 47 mph alone is Severe

    def test_asks_for_49_hours_plus_the_last_precipitation_stamp(self):
        use_case, forecast, trip = setup()
        use_case(trip.id, now=utc(14, 35))
        _, start, end = forecast.calls[0]
        self.assertEqual(start, utc(14))
        self.assertEqual(end, utc(14) + timedelta(hours=HOURS))  # hour 48 + 1 h

    def test_second_request_in_the_same_hour_is_served_from_cache(self):
        use_case, forecast, trip = setup()
        use_case(trip.id, now=utc(14, 5))
        use_case(trip.id, now=utc(14, 50))
        self.assertEqual(len(forecast.calls), 1)

    def test_a_new_clock_hour_builds_a_new_heatmap(self):
        use_case, forecast, trip = setup()
        use_case(trip.id, now=utc(14, 5))
        later = use_case(trip.id, now=utc(15, 5))
        self.assertEqual(len(forecast.calls), 2)
        self.assertEqual(later.hours[0], utc(15))

    def test_unknown_trip(self):
        use_case, forecast, _ = setup()
        with self.assertRaises(TripNotFound):
            use_case(uuid4())
        self.assertEqual(forecast.calls, [])
