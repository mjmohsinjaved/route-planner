"""TripRepository over the TripPlan model: inputs in columns, the rest stored whole as JSON."""
from uuid import UUID

from ..application.dto import trip_from_payload, trip_to_payload
from ..domain.entities import Trip
from ..domain.errors import TripNotFound
from ..domain.timeutil import iso_z
from ..models import TripPlan

COLUMNS = ("id", "origin", "destination", "departure", "load_lb", "interval_mi")


class DjangoTripRepository:
    def add(self, trip: Trip) -> None:
        payload = trip_to_payload(trip)
        TripPlan.objects.create(
            id=trip.id,
            origin=payload["origin"],
            destination=payload["destination"],
            departure=trip.departure,
            load_lb=trip.load_lb,
            interval_mi=trip.interval_mi,
            result={k: v for k, v in payload.items() if k not in COLUMNS},
        )

    def get(self, trip_id: UUID) -> Trip:
        try:
            row = TripPlan.objects.get(id=trip_id)
        except TripPlan.DoesNotExist:
            raise TripNotFound("Not found.") from None
        return trip_from_payload(
            {
                "id": str(row.id),
                "origin": row.origin,
                "destination": row.destination,
                "departure": iso_z(row.departure),
                "load_lb": row.load_lb,
                "interval_mi": row.interval_mi,
                **row.result,
            }
        )
