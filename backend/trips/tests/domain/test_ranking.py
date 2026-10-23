from django.test import SimpleTestCase

from trips.domain.entities import AssessedCheckpoint, Checkpoint, Conditions, Risk, RouteAssessment, RouteMetrics
from trips.domain.ranking import recommend, route_metrics

from ..fakes import DEPART


def cp(score, seg):
    checkpoint = Checkpoint(index=0, mile=0, segment_mi=seg, lat=0, lon=0, eta=DEPART)
    conditions = Conditions(wind_mph=0, gust_mph=None, rain_in_hr=0, snow_in_hr=0)
    return AssessedCheckpoint(checkpoint, conditions, Risk("-", score, "-"))


def route(rid, no_travel=0, severe=0, high=0, avg=0.0, minutes=600):
    return RouteAssessment(
        id=rid,
        distance_mi=0,
        duration_min=minutes,
        arrival=DEPART,
        metrics=RouteMetrics(no_travel_mi=no_travel, severe_mi=severe, high_mi=high, avg_risk=avg),
        geometry=[],
        checkpoints=[],
    )


class MetricsTests(SimpleTestCase):
    def test_miles_per_level_and_weighted_average(self):
        checkpoints = [cp(0, 0), cp(0, 25), cp(2, 25), cp(3, 25), cp(4, 25)]
        m = route_metrics(checkpoints)
        self.assertEqual(m.high_mi, 25)
        self.assertEqual(m.severe_mi, 25)
        self.assertEqual(m.no_travel_mi, 25)
        self.assertEqual(m.avg_risk, 2.25)  # (0+2+3+4)*25 / 100

    def test_origin_level_does_not_count_miles(self):
        m = route_metrics([cp(4, 0), cp(0, 10)])
        self.assertEqual(m.no_travel_mi, 0)


class RankingTests(SimpleTestCase):
    def test_fewest_no_travel_miles_first(self):
        r = recommend([route("A", no_travel=10, minutes=500), route("B", severe=50, minutes=700)])
        self.assertEqual(r.recommended_route_id, "B")
        self.assertIn("no No Travel miles vs 10.0 on Route A", r.reason)

    def test_fewest_severe_miles(self):
        r = recommend([route("A", severe=42, minutes=500), route("B", severe=0, high=90, minutes=518)])
        self.assertEqual(r.recommended_route_id, "B")
        self.assertEqual(
            r.reason,
            "Route B recommended: no Severe miles vs 42.0 on Route A, 18 min longer than the fastest (Route A).",
        )

    def test_fewest_high_miles(self):
        r = recommend([route("A", high=30), route("B", high=10, minutes=700)])
        self.assertEqual(r.recommended_route_id, "B")
        self.assertIn("10.0 High miles vs 30.0 on Route A", r.reason)

    def test_fractional_miles_are_not_shown_as_zero(self):
        r = recommend([route("A", severe=0.4), route("B", severe=0.0, minutes=700)])
        self.assertIn("no Severe miles vs 0.4 on Route A", r.reason)

    def test_lowest_average_risk(self):
        r = recommend([route("A", avg=0.9), route("B", avg=0.4, minutes=700)])
        self.assertEqual(r.recommended_route_id, "B")
        self.assertIn("lower average risk (0.40 vs 0.90 on Route A)", r.reason)

    def test_shortest_time_when_risk_is_equal(self):
        r = recommend([route("A", minutes=700), route("B", minutes=650), route("C", minutes=800)])
        self.assertEqual(r.recommended_route_id, "B")
        self.assertEqual(r.ranking, ["B", "A", "C"])
        self.assertIn("faster (10 h 50 min vs 11 h 40 min)", r.reason)

    def test_winner_that_is_also_fastest(self):
        r = recommend([route("A", severe=0, minutes=500), route("B", severe=20, minutes=600)])
        self.assertTrue(r.reason.endswith("and it is also the fastest."))

    def test_full_tie(self):
        r = recommend([route("A"), route("B")])
        self.assertEqual(r.recommended_route_id, "A")
        self.assertIn("ties with Route B", r.reason)


class UnsafeFlagTests(SimpleTestCase):
    def test_unsafe_when_every_route_has_no_travel(self):
        r = recommend([route("A", no_travel=5), route("B", no_travel=20)])
        self.assertTrue(r.unsafe)
        self.assertEqual(r.recommended_route_id, "A")
        self.assertIn("Every route crosses No Travel weather", r.reason)

    def test_safe_when_one_route_avoids_no_travel(self):
        r = recommend([route("A", no_travel=5), route("B")])
        self.assertFalse(r.unsafe)
