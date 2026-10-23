from django.core.cache import cache
from django.test import TestCase

from trips.container import build_container, using_container
from trips.domain.entities import Place
from trips.domain.errors import GeocodingUnavailable

from ..fakes import FakeGeocoder, InMemoryCache

CHICAGO = Place("Chicago, IL, USA", 41.8781, -87.6298)


class GeocodeEndpointTests(TestCase):
    def setUp(self):
        cache.clear()

    def serve(self, geocoder):
        context = using_container(build_container(geocoder=geocoder, cache=InMemoryCache()))
        context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)

    def test_returns_name_lat_lon(self):
        self.serve(FakeGeocoder([CHICAGO]))
        res = self.client.get("/api/geocode/", {"q": "chicago"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [{"name": "Chicago, IL, USA", "lat": 41.8781, "lon": -87.6298}])

    def test_short_or_missing_query_is_an_empty_list(self):
        geocoder = FakeGeocoder([CHICAGO])
        self.serve(geocoder)
        self.assertEqual(self.client.get("/api/geocode/", {"q": "c"}).json(), [])
        self.assertEqual(self.client.get("/api/geocode/").json(), [])
        self.assertEqual(geocoder.calls, [])

    def test_provider_failure_is_502_with_a_geocoding_message(self):
        class Down:
            def search(self, query, limit):
                raise GeocodingUnavailable()

        self.serve(Down())
        res = self.client.get("/api/geocode/", {"q": "chicago"})
        self.assertEqual(res.status_code, 502)
        self.assertEqual(res.json()["detail"], "Geocoding service is unavailable. Try again.")


class HealthTests(TestCase):
    def test_ok(self):
        self.assertEqual(self.client.get("/api/health/").json(), {"status": "ok"})
