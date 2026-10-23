"""
HTTP endpoints. Each view throttles, validates, calls one use case and shapes
the response. Domain errors are mapped to statuses in exception_handler.py.
"""
from uuid import UUID

from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

from ...application.dto import PlanTripCommand, heatmap_to_payload, trip_to_payload
from ...domain.entities import Place
from ...container import get_container
from . import throttling
from .serializers import TripRequestSerializer


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
@throttle_classes(throttling.GEOCODE)
def geocode_view(request):
    places = get_container().suggest_places(request.query_params.get("q", ""))
    return Response([{"name": p.name, "lat": p.lat, "lon": p.lon} for p in places])


@api_view(["POST"])
@throttle_classes(throttling.PLAN)
def trip_create(request):
    serializer = TripRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    trip = get_container().plan_trip(
        PlanTripCommand(
            origin=Place(**data["origin"]),
            destination=Place(**data["destination"]),
            departure=data["departure"],
            load_lb=data["load_lb"],
            interval_mi=data["interval_mi"],
        )
    )
    return Response(trip_to_payload(trip), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@throttle_classes(throttling.READ)
def trip_detail(request, trip_id: UUID):
    return Response(trip_to_payload(get_container().get_trip(trip_id)))


@api_view(["GET"])
@throttle_classes(throttling.READ)
def trip_heatmap(request, trip_id: UUID):
    return Response(heatmap_to_payload(get_container().build_heatmap(trip_id)))
