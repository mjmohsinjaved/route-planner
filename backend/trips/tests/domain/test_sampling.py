from datetime import timedelta

from django.test import SimpleTestCase

from trips.domain.geo import METERS_PER_MILE, encode_polyline, interpolate
from trips.domain.sampling import sample_checkpoints

from ..fakes import DEPART, straight_route


class SamplingTests(SimpleTestCase):
    def test_includes_origin_every_interval_and_destination(self):
        cps = sample_checkpoints(straight_route(100, 2), 25, DEPART)
        self.assertEqual([c.mile for c in cps], [0.0, 25.0, 50.0, 75.0, 100.0])

    def test_last_segment_is_the_remainder(self):
        cps = sample_checkpoints(straight_route(60, 1), 25, DEPART)
        self.assertEqual([c.mile for c in cps], [0.0, 25.0, 50.0, 60.0])
        self.assertAlmostEqual(cps[-1].segment_mi, 10.0, places=1)

    def test_segments_add_up_to_route_length(self):
        route = straight_route(137, 3)
        for interval in (10, 25, 50):
            with self.subTest(interval=interval):
                cps = sample_checkpoints(route, interval, DEPART)
                total = sum(c.segment_mi for c in cps)
                self.assertAlmostEqual(total, route.distance_m / METERS_PER_MILE, places=1)
                self.assertEqual(cps[0].segment_mi, 0.0)

    def test_short_trip_has_origin_and_destination_only(self):
        cps = sample_checkpoints(straight_route(8, 0.2), 10, DEPART)
        self.assertEqual(len(cps), 2)

    def test_eta_from_route_time_not_average_speed(self):
        cps = sample_checkpoints(straight_route(100, 4, slow_first_half=True), 50, DEPART)
        # Halfway point reached after 75% of 4 h = 3 h, not 2 h
        self.assertEqual(cps[1].eta, DEPART + timedelta(hours=3))
        self.assertEqual(cps[-1].eta, DEPART + timedelta(hours=4))
        self.assertEqual(cps[0].eta, DEPART)

    def test_checkpoint_positions_are_on_the_route(self):
        cps = sample_checkpoints(straight_route(100, 2), 50, DEPART)
        self.assertAlmostEqual(cps[1].lat, 40.0 + 50 / 69.05, places=2)
        self.assertEqual(cps[1].lon, -100.0)

    def test_rejects_unknown_interval(self):
        with self.assertRaises(ValueError):
            sample_checkpoints(straight_route(100, 2), 30, DEPART)


class GeoHelperTests(SimpleTestCase):
    def test_interpolate(self):
        self.assertEqual(interpolate(5, [0, 10], [0, 100]), 50)
        self.assertEqual(interpolate(-1, [0, 10], [0, 100]), 0)
        self.assertEqual(interpolate(11, [0, 10], [0, 100]), 100)

    def test_encode_polyline_matches_google_reference(self):
        points = [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]
        self.assertEqual(encode_polyline(points), "_p~iF~ps|U_ulLnnqC_mqNvxq`@")
