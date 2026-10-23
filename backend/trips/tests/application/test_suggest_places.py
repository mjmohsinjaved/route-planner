from django.test import SimpleTestCase

from trips.application.suggest_places import SuggestPlaces
from trips.domain.entities import Place

from ..fakes import FakeGeocoder, InMemoryCache

CHICAGO = Place("Chicago, IL, USA", 41.8781, -87.6298)


class SuggestPlacesTests(SimpleTestCase):
    def setUp(self):
        self.geocoder = FakeGeocoder([CHICAGO])
        self.suggest = SuggestPlaces(self.geocoder, InMemoryCache())

    def test_short_text_returns_nothing_without_a_lookup(self):
        self.assertEqual(self.suggest("c"), [])
        self.assertEqual(self.suggest("   "), [])
        self.assertEqual(self.geocoder.calls, [])

    def test_returns_places_and_passes_the_limit(self):
        self.assertEqual(self.suggest("chicago"), [CHICAGO])
        self.assertEqual(self.geocoder.calls, [("chicago", 5)])

    def test_same_text_in_any_case_is_cached(self):
        self.suggest("Chicago")
        self.suggest(" chicago ")
        self.assertEqual(len(self.geocoder.calls), 1)
