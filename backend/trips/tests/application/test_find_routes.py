from django.test import SimpleTestCase

from trips.application.find_routes import FindRoutes
from trips.domain.entities import Place, Route
from trips.domain.errors import NoRouteFound, ProviderUnavailable
from trips.domain.vehicle_rules import VIA_ROUNDS, vehicle_weight_kg

from ..fakes import DEPART, FakeRoutes, InMemoryCache

ORIGIN = Place("A", 40.0, -100.0)
DEST = Place("B", 42.0, -100.0)


def route(length_m: int, time_s: int) -> Route:
    return Route(
        id="",
        distance_m=length_m,
        duration_s=time_s,
        points=[(40.0, -100.0), (42.0, -100.0)],
        time_anchors=[(0, 0), (length_m, time_s)],
    )


def find(respond):
    provider = FakeRoutes(respond)
    return FindRoutes(provider, InMemoryCache()), provider


class FindRoutesTests(SimpleTestCase):
    def test_three_distinct_routes_need_no_fallback(self):
        find_routes, provider = find(lambda *a: [route(100_000, 3600), route(110_000, 4000), route(120_000, 4400)])
        routes = find_routes(ORIGIN, DEST, DEPART, 38_000)
        self.assertEqual([r.id for r in routes], ["A", "B", "C"])
        self.assertEqual(routes[0].distance_mi, 62.1)
        self.assertEqual(routes[0].duration_min, 60)
        self.assertEqual(len(provider.calls), 1)

    def test_direct_request_asks_for_two_alternatives_with_the_whole_truck_weight(self):
        find_routes, provider = find(lambda *a: [route(100_000, 3600), route(110_000, 4000), route(120_000, 4400)])
        find_routes(ORIGIN, DEST, DEPART, 38_000)
        waypoints, depart_at, kg, alternatives = provider.calls[0]
        self.assertEqual(waypoints, [ORIGIN.latlon, DEST.latlon])
        self.assertEqual(depart_at, DEPART)
        self.assertEqual(kg, vehicle_weight_kg(38_000))
        self.assertEqual(alternatives, 2)

    def test_fallback_drops_duplicates_and_tries_a_second_round(self):
        def respond(waypoints, depart_at, kg, alternatives):
            if len(waypoints) == 2:  # the direct request: only one route came back
                return [route(100_000, 3600)]
            detour = round(abs(waypoints[1][1] + 100.0) * 100_000)  # same |offset| -> same length -> duplicate
            return [route(100_000 + detour, 3600 + detour // 20)]

        find_routes, provider = find(respond)
        routes = find_routes(ORIGIN, DEST, DEPART, 38_000)

        # direct + both via-points of round one (duplicates of each other) + both of round two
        self.assertEqual(len(provider.calls), 1 + sum(len(r) for r in VIA_ROUNDS))
        self.assertEqual([r.id for r in routes], ["A", "B", "C"])
        self.assertEqual(len({r.distance_m for r in routes}), 3)

    def test_second_round_is_skipped_when_the_first_fills_the_gap(self):
        def respond(waypoints, depart_at, kg, alternatives):
            if len(waypoints) == 2:
                return [route(100_000, 3600)]
            signed = round((waypoints[1][1] + 100.0) * 100_000)  # left and right detours differ
            return [route(120_000 + signed, 4000 + signed // 20)]

        find_routes, provider = find(respond)
        routes = find_routes(ORIGIN, DEST, DEPART, 38_000)

        self.assertEqual(len(provider.calls), 1 + len(VIA_ROUNDS[0]))
        self.assertEqual([r.id for r in routes], ["A", "B", "C"])

    def test_a_via_point_that_cannot_be_routed_is_skipped(self):
        def respond(waypoints, depart_at, kg, alternatives):
            if len(waypoints) == 2:
                return [route(100_000, 3600)]
            return ProviderUnavailable()  # e.g. the via-point landed in a lake

        find_routes, _ = find(respond)
        routes = find_routes(ORIGIN, DEST, DEPART, 38_000)
        self.assertEqual([r.id for r in routes], ["A"])  # fewer than 3, but the trip still plans

    def test_routes_are_cached_per_hour_and_load(self):
        find_routes, provider = find(lambda *a: [route(100_000, 3600), route(110_000, 4000), route(120_000, 4400)])
        first = find_routes(ORIGIN, DEST, DEPART, 38_000)
        again = find_routes(ORIGIN, DEST, DEPART.replace(minute=40), 38_000)  # same hour
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual([r.id for r in again], [r.id for r in first])

        find_routes(ORIGIN, DEST, DEPART, 20_000)  # different load -> new request
        self.assertEqual(len(provider.calls), 2)

    def test_no_route_raises(self):
        find_routes, _ = find(lambda *a: [])
        with self.assertRaises(NoRouteFound):
            find_routes(ORIGIN, DEST, DEPART, 38_000)
