from unittest import mock

import httpx
from django.test import SimpleTestCase, override_settings

from trips.domain.errors import GeocodingUnavailable, ProviderUnavailable
from trips.infrastructure import http
from trips.infrastructure.tomtom_geocoder import TomTomGeocoder
from trips.infrastructure.tomtom_routing import TomTomRouting, parse_route

from ..fakes import DEPART


def raw_route(length_m=100_000, time_s=3600, instructions=None):
    raw = {
        "summary": {"lengthInMeters": length_m, "travelTimeInSeconds": time_s},
        "legs": [{"points": [{"latitude": 40.0, "longitude": -100.0}, {"latitude": 42.0, "longitude": -100.0}]}],
    }
    if instructions is not None:
        raw["guidance"] = {"instructions": instructions}
    return raw


def ok(payload):
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://api.tomtom.com"))


class ParseRouteTests(SimpleTestCase):
    def test_keeps_geometry_and_sorted_time_anchors(self):
        route = parse_route(
            raw_route(instructions=[
                {"routeOffsetInMeters": 60_000, "travelTimeInSeconds": 2_000},
                {"routeOffsetInMeters": 30_000, "travelTimeInSeconds": 1_000},
                {"routeOffsetInMeters": 30_000, "travelTimeInSeconds": 1_000},  # duplicate instruction point
            ])
        )
        self.assertEqual(route.id, "")  # ids are given once the set of routes is final
        self.assertEqual((route.distance_m, route.duration_s), (100_000, 3600))
        self.assertEqual(route.points, [(40.0, -100.0), (42.0, -100.0)])
        self.assertEqual(route.time_anchors, [(0, 0), (30_000, 1_000), (60_000, 2_000), (100_000, 3_600)])

    def test_a_route_without_instructions_still_has_start_and_end_anchors(self):
        self.assertEqual(parse_route(raw_route()).time_anchors, [(0, 0), (100_000, 3600)])


@override_settings(TOMTOM_API_KEY="the-key")
class TomTomRoutingTests(SimpleTestCase):
    @mock.patch.object(http.httpx, "get")
    def test_sends_a_truck_request_with_weight_departure_and_waypoints(self, get):
        get.return_value = ok({"routes": [raw_route(), raw_route(110_000, 4000)]})
        routes = TomTomRouting().calculate([(41.0, -87.0), (39.0, -104.0)], DEPART, 33_000, 2)

        self.assertEqual(len(routes), 2)
        url = get.call_args.args[0]
        params = get.call_args.kwargs["params"]
        self.assertTrue(url.endswith("/41.0,-87.0:39.0,-104.0/json"))
        self.assertEqual(params["travelMode"], "truck")
        self.assertEqual(params["vehicleWeight"], 33_000)
        self.assertEqual(params["maxAlternatives"], 2)
        self.assertEqual(params["departAt"], "2026-10-21T08:00:00+00:00")
        self.assertEqual(params["key"], "the-key")

    @mock.patch.object(http.httpx, "get")
    def test_no_routes_in_the_response_is_an_empty_list(self, get):
        get.return_value = ok({"routes": []})
        self.assertEqual(TomTomRouting().calculate([(41.0, -87.0), (39.0, -104.0)], DEPART, 33_000, 2), [])

    @mock.patch.object(http.httpx, "get", return_value=httpx.Response(403, request=httpx.Request("GET", "https://x/?key=the-key")))
    def test_a_rejected_request_is_provider_unavailable_without_the_key(self, get):
        with self.assertRaises(ProviderUnavailable) as ctx:
            TomTomRouting().calculate([(41.0, -87.0), (39.0, -104.0)], DEPART, 33_000, 2)
        self.assertNotIn("the-key", str(ctx.exception))


@override_settings(TOMTOM_API_KEY="the-key")
class TomTomGeocoderTests(SimpleTestCase):
    @mock.patch.object(http.httpx, "get")
    def test_maps_results_to_places(self, get):
        get.return_value = ok({"results": [
            {"address": {"freeformAddress": "Chicago, IL, USA"}, "position": {"lat": 41.8781, "lon": -87.6298}},
            {"address": {}, "position": {"lat": 1.0, "lon": 2.0}},
        ]})
        places = TomTomGeocoder().search("chicago", 5)
        self.assertEqual([(p.name, p.lat, p.lon) for p in places], [("Chicago, IL, USA", 41.8781, -87.6298), ("chicago", 1.0, 2.0)])
        params = get.call_args.kwargs["params"]
        self.assertEqual((params["limit"], params["countrySet"], params["typeahead"]), (5, "US,CA", "true"))

    @mock.patch.object(http.httpx, "get")
    def test_the_query_is_one_url_path_segment(self, get):
        get.return_value = ok({"results": []})
        TomTomGeocoder().search("../../etc/passwd", 5)
        url = get.call_args.args[0]
        self.assertNotIn("../", url)
        self.assertIn("..%2F..%2Fetc%2Fpasswd", url)

    @mock.patch.object(http.httpx, "get", side_effect=httpx.ConnectError("down"))
    def test_failures_are_geocoding_unavailable_and_not_retried(self, get):
        with self.assertRaises(GeocodingUnavailable):
            TomTomGeocoder().search("chicago", 5)
        get.assert_called_once()
