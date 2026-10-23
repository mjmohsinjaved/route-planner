from datetime import timedelta

from django.test import SimpleTestCase

from trips.domain.errors import ForecastMissing
from trips.domain.geo import KM_PER_DEG_LAT
from trips.domain.heatmap_grid import CELL_DEG, HOURS, corridor_points, hour_range, score_hours

from ..fakes import series, utc


def north_line(km: float, lon: float = -100.0, start_lat: float = 40.0, n: int = 100):
    """A due-north polyline `km` long with n+1 points."""
    return [(start_lat + i * (km / KM_PER_DEG_LAT) / n, lon) for i in range(n + 1)]


class GridTests(SimpleTestCase):
    def test_points_along_the_route_plus_30km_each_side(self):
        pts = corridor_points([north_line(200)])
        center = [p for p in pts if p[1] == -100.0]
        # Samples every 25 km over 200 km fall into 5 distinct 0.5° latitude cells
        self.assertEqual(len(center), 5)
        self.assertEqual((center[0][0], center[-1][0]), (40.0, 42.0))
        # 30 km east/west at ~41° N is ~0.36° of longitude, snapped to the 0.5° grid
        self.assertEqual({p[1] for p in pts}, {-100.5, -100.0, -99.5})
        self.assertEqual(len(pts), 15)

    def test_points_are_snapped_to_cells_and_unique(self):
        pts = corridor_points([north_line(200)])
        self.assertEqual(len(pts), len(set(pts)))
        for lat, lon in pts:
            self.assertEqual((round(lat, 1), round(lon, 1)), (lat, lon))
            self.assertAlmostEqual(round(lat / CELL_DEG) * CELL_DEG, lat, places=6)
            self.assertAlmostEqual(round(lon / CELL_DEG) * CELL_DEG, lon, places=6)

    def test_overlapping_routes_share_points(self):
        one = corridor_points([north_line(200)])
        twice = corridor_points([north_line(200), north_line(200)])
        self.assertEqual(one, twice)

    def test_shared_stretch_is_counted_once(self):
        # Two routes that share their first 200 km, then split 50 km apart for 200 km
        shared = north_line(200)
        left = shared + north_line(200, lon=-100.6, start_lat=41.8)[1:]
        right = shared + north_line(200, lon=-99.4, start_lat=41.8)[1:]
        both = corridor_points([left, right])
        alone = corridor_points([left])
        self.assertLess(len(both), 2 * len(alone))
        self.assertEqual(len(both), len(set(both)))


class ScoreTests(SimpleTestCase):
    def test_49_hours_from_the_current_hour(self):
        hours = hour_range(utc(14, 35))
        self.assertEqual(len(hours), HOURS)
        self.assertEqual(hours[0], utc(14))
        self.assertEqual(hours[-1], utc(14) + timedelta(hours=48))

    def test_scores_apply_wind_precip_and_load_rules(self):
        windy, calm = (41.0, -87.0), (42.0, -90.0)
        hours = hour_range(utc(14))
        rain = [0.0] * 50
        rain[6] = 1.5  # stamped 20:00 -> covers 19:00-20:00 -> hour index 5
        data = {windy: series(utc(14), 50, wind=47.0), calm: series(utc(14), 50, rain=rain)}

        heavy = score_hours([windy, calm], hours, data, load_lb=38_000)
        self.assertEqual(len(heavy), HOURS)
        self.assertTrue(all(row[0] == 4 for row in heavy))  # 47 mph + 38,000 lb -> No Travel
        self.assertEqual(heavy[5][1], 4)  # > 1.00 in/hr rain -> No Travel
        self.assertEqual(heavy[4][1], 0)
        self.assertEqual(heavy[6][1], 0)

        light = score_hours([windy, calm], hours, data, load_lb=20_000)
        self.assertTrue(all(row[0] == 3 for row in light))  # 47 mph alone -> Severe

    def test_missing_hour_is_an_error(self):
        point = (41.0, -87.0)
        hours = hour_range(utc(14))
        with self.assertRaises(ForecastMissing):
            score_hours([point], hours, {point: series(utc(14), 10)}, load_lb=1)
