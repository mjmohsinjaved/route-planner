from django.test import SimpleTestCase

from trips.application.dto import heatmap_to_payload, trip_from_payload, trip_to_payload
from trips.domain.entities import Heatmap

from ..fakes import utc
from .test_plan_trip import command, planner


class TripPayloadTests(SimpleTestCase):
    def setUp(self):
        use_case, _, _ = planner()
        self.trip = use_case(command())
        self.payload = trip_to_payload(self.trip)

    def test_payload_has_the_documented_fields(self):
        for key in ("id", "origin", "destination", "departure", "load_lb", "interval_mi",
                    "recommended_route_id", "ranking", "recommendation_reason", "unsafe", "routes"):
            self.assertIn(key, self.payload)
        route = self.payload["routes"][0]
        for key in ("id", "distance_mi", "duration_min", "arrival", "no_travel_mi", "severe_mi",
                    "high_mi", "avg_risk", "geometry", "checkpoints"):
            self.assertIn(key, route)
        for key in ("index", "mile", "segment_mi", "lat", "lon", "eta", "wind_mph", "gust_mph",
                    "rain_in_hr", "snow_in_hr", "level", "level_score", "reason"):
            self.assertIn(key, route["checkpoints"][0])
        self.assertTrue(route["checkpoints"][0]["eta"].endswith("Z"))
        self.assertTrue(self.payload["departure"].endswith("Z"))
        self.assertIsInstance(route["geometry"], str)

    def test_a_stored_payload_rebuilds_the_same_payload(self):
        again = trip_to_payload(trip_from_payload(self.payload))
        self.assertEqual(again, self.payload)


class HeatmapPayloadTests(SimpleTestCase):
    def test_shape(self):
        payload = heatmap_to_payload(Heatmap(points=[(41.0, -87.0)], hours=[utc(14)], values=[[2]]))
        self.assertEqual(payload, {"points": [[41.0, -87.0]], "hours": ["2026-10-21T14:00:00Z"], "values": [[2]]})
