from uuid import uuid4

from django.test import TestCase

from trips.application.dto import trip_to_payload
from trips.domain.errors import TripNotFound
from trips.infrastructure.django_trip_repo import DjangoTripRepository
from trips.models import TripPlan

from ..application.test_plan_trip import command, planner


class DjangoTripRepositoryTests(TestCase):
    def setUp(self):
        use_case, _, _ = planner()
        self.trip = use_case(command())
        self.repo = DjangoTripRepository()

    def test_a_saved_trip_comes_back_as_the_same_payload(self):
        self.repo.add(self.trip)
        self.assertEqual(trip_to_payload(self.repo.get(self.trip.id)), trip_to_payload(self.trip))

    def test_inputs_are_columns_and_the_rest_is_stored_whole(self):
        self.repo.add(self.trip)
        row = TripPlan.objects.get(id=self.trip.id)
        self.assertEqual(row.load_lb, 38_000)
        self.assertEqual(row.interval_mi, 25)
        self.assertEqual(row.origin["name"], "Chicago, IL")
        self.assertEqual(set(row.result), {"recommended_route_id", "ranking", "recommendation_reason", "unsafe", "routes"})

    def test_unknown_id(self):
        with self.assertRaises(TripNotFound):
            self.repo.get(uuid4())
