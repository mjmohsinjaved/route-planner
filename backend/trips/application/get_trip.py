"""Reopen a saved trip."""
from uuid import UUID

from ..domain.entities import Trip
from .ports import TripRepository


class GetTrip:
    def __init__(self, trips: TripRepository):
        self.trips = trips

    def __call__(self, trip_id: UUID) -> Trip:
        return self.trips.get(trip_id)
