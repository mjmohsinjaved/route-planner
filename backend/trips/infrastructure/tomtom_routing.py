"""RoutePort over the TomTom Routing API (truck mode)."""
from datetime import datetime
from typing import Sequence

from django.conf import settings

from ..domain.entities import LatLon, Route
from . import http

ROUTE_URL = "https://api.tomtom.com/routing/1/calculateRoute/{locations}/json"
TIMEOUT_SECONDS = 20


def parse_route(raw: dict) -> Route:
    """Keep only what we need: geometry plus distance/time anchors along it."""
    summary = raw["summary"]
    points = [(p["latitude"], p["longitude"]) for leg in raw["legs"] for p in leg["points"]]

    # (meters from start, seconds from start) pairs, used later to compute ETAs
    anchors = [(0, 0)]
    for step in raw.get("guidance", {}).get("instructions", []):
        anchors.append((step["routeOffsetInMeters"], step["travelTimeInSeconds"]))
    anchors.append((summary["lengthInMeters"], summary["travelTimeInSeconds"]))

    return Route(
        id="",
        distance_m=summary["lengthInMeters"],
        duration_s=summary["travelTimeInSeconds"],
        points=points,
        time_anchors=sorted(set(anchors)),
    )


class TomTomRouting:
    def calculate(
        self, waypoints: Sequence[LatLon], depart_at: datetime, vehicle_weight_kg: int, max_alternatives: int
    ) -> list[Route]:
        locations = ":".join(f"{lat},{lon}" for lat, lon in waypoints)
        params = {
            "key": settings.TOMTOM_API_KEY,
            "travelMode": "truck",
            "vehicleWeight": vehicle_weight_kg,
            "maxAlternatives": max_alternatives,
            "departAt": depart_at.isoformat(timespec="seconds"),
            "routeRepresentation": "polyline",
            "instructionsType": "coded",  # gives cumulative time along the route
        }
        response = http.get(ROUTE_URL.format(locations=locations), params=params, timeout=TIMEOUT_SECONDS)
        return [parse_route(raw) for raw in http.json_or_raise(response).get("routes", [])]
