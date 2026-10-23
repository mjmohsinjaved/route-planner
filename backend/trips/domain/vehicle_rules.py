"""Routing rules that need no I/O: vehicle weight, duplicate routes, via-points."""
from .entities import LatLon, Route
from .geo import offset_km, unit_east_north

LB_TO_KG = 0.45359237
TRUCK_TARE_LB = 35_000  # empty tractor-trailer; added to the load for the vehicle weight
TARGET_ROUTES = 3
# Sideways via-points tried when the provider gives < 3 routes: one round each, nearer pair first.
VIA_ROUNDS = ((1, -1), (1.8, -1.8))
DUPLICATE_TOLERANCE = 0.01


def vehicle_weight_kg(load_lb: float) -> int:
    """The whole truck, not just the cargo: road restrictions apply to both."""
    return round((load_lb + TRUCK_TARE_LB) * LB_TO_KG)


def is_duplicate(candidate: Route, routes: list[Route]) -> bool:
    """Routes within 1% on both distance and time count as the same route."""
    for r in routes:
        same_distance = abs(candidate.distance_m - r.distance_m) / r.distance_m < DUPLICATE_TOLERANCE
        same_time = abs(candidate.duration_s - r.duration_s) / r.duration_s < DUPLICATE_TOLERANCE
        if same_distance and same_time:
            return True
    return False


def add_distinct(routes: list[Route], candidates: list[Route]) -> None:
    """Append candidates that are not duplicates, up to TARGET_ROUTES."""
    for candidate in candidates:
        if len(routes) >= TARGET_ROUTES:
            return
        if not is_duplicate(candidate, routes):
            routes.append(candidate)


def via_offset_km(base: Route) -> float:
    """How far to the side to put a via-point: 10% of the route length, between 30 and 80 km."""
    return max(30, min(80, base.distance_m / 1000 * 0.1))


def via_point(origin: LatLon, destination: LatLon, midpoint: LatLon, offset_km_: float) -> LatLon:
    """A point offset sideways from the route midpoint (positive = left of travel)."""
    east, north = unit_east_north(origin, destination)
    return offset_km(midpoint, -north * offset_km_, east * offset_km_)
