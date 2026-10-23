"""
Composition root: the one place that knows which adapter fills each port.

Views call `get_container()`. Tests build a container with fakes and install it
with `using_container(...)`, so no HTTP library needs patching.
"""
from contextlib import contextmanager
from dataclasses import dataclass

from .application.build_heatmap import BuildHeatmap
from .application.find_routes import FindRoutes
from .application.get_trip import GetTrip
from .application.plan_trip import PlanTrip
from .application.ports import CachePort, ForecastPort, GeocoderPort, RoutePort, TripRepository
from .application.suggest_places import SuggestPlaces


@dataclass(frozen=True)
class Container:
    plan_trip: PlanTrip
    get_trip: GetTrip
    build_heatmap: BuildHeatmap
    suggest_places: SuggestPlaces


def build_container(
    *,
    routes: RoutePort | None = None,
    forecast: ForecastPort | None = None,
    geocoder: GeocoderPort | None = None,
    trips: TripRepository | None = None,
    cache: CachePort | None = None,
) -> Container:
    """Wire the use cases. Any port left out gets its production adapter."""
    # Imported here so that importing the container does not load Django models before apps are ready
    from .infrastructure.django_cache import DjangoCache
    from .infrastructure.django_trip_repo import DjangoTripRepository
    from .infrastructure.openmeteo_forecast import OpenMeteoForecast
    from .infrastructure.tomtom_geocoder import TomTomGeocoder
    from .infrastructure.tomtom_routing import TomTomRouting

    cache = cache or DjangoCache()
    routes = routes or TomTomRouting()
    forecast = forecast or OpenMeteoForecast(cache)
    geocoder = geocoder or TomTomGeocoder()
    trips = trips or DjangoTripRepository()
    return Container(
        plan_trip=PlanTrip(FindRoutes(routes, cache), forecast, trips),
        get_trip=GetTrip(trips),
        build_heatmap=BuildHeatmap(trips, forecast, cache),
        suggest_places=SuggestPlaces(geocoder, cache),
    )


_current: Container | None = None


def get_container() -> Container:
    global _current
    if _current is None:
        _current = build_container()
    return _current


@contextmanager
def using_container(container: Container):
    """Install `container` for the duration of the block (tests)."""
    global _current
    previous, _current = _current, container
    try:
        yield container
    finally:
        _current = previous
