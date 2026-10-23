"""Find 3 distinct truck routes: ask the provider for alternatives, then fall back to via-points."""
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime

from ..domain.entities import Place, Route
from ..domain.errors import NoRouteFound, ProviderError
from ..domain.timeutil import floor_hour
from ..domain.vehicle_rules import TARGET_ROUTES, VIA_ROUNDS, add_distinct, via_offset_km, via_point, vehicle_weight_kg
from .ports import CachePort, RoutePort
from .stopwatch import Stopwatch

logger = logging.getLogger(__name__)

CACHE_SECONDS = 60 * 60


class FindRoutes:
    """Exactly 3 distinct routes, or fewer only if no more can be found. Cached for an hour."""

    def __init__(self, provider: RoutePort, cache: CachePort):
        self.provider = provider
        self.cache = cache

    def __call__(self, origin: Place, destination: Place, depart_at: datetime, load_lb: int) -> list[Route]:
        key = self._cache_key(origin, destination, depart_at, load_lb)
        return self.cache.get_or_set(key, lambda: self._fetch(origin, destination, depart_at, load_lb), CACHE_SECONDS)

    @staticmethod
    def _cache_key(o: Place, d: Place, depart_at: datetime, load_lb: int) -> str:
        hour = floor_hour(depart_at)
        return f"routes:{o.lat:.4f},{o.lon:.4f}:{d.lat:.4f},{d.lon:.4f}:{int(hour.timestamp())}:{int(load_lb)}"

    def _fetch(self, origin: Place, destination: Place, depart_at: datetime, load_lb: int) -> list[Route]:
        clock = Stopwatch()
        o, d = origin.latlon, destination.latlon
        kg = vehicle_weight_kg(load_lb)

        routes: list[Route] = []
        found = self.provider.calculate([o, d], depart_at, kg, TARGET_ROUTES - 1)
        add_distinct(routes, found)
        clock.lap(f"direct ({len(found)} routes, {len(routes)} distinct)")
        if not routes:
            raise NoRouteFound("No truck route found between these places.")

        # Fallback: each round fires its via-points in parallel; a second round only if still short
        for factors in VIA_ROUNDS:
            if len(routes) >= TARGET_ROUTES:
                break
            for candidates in self._via_candidates(o, d, routes[0], depart_at, kg, factors):
                add_distinct(routes, candidates)
            clock.lap(f"via-points {factors} (now {len(routes)})")

        logger.info("routing: %s", clock.summary())
        return [replace(route, id=label) for label, route in zip("ABC", routes)]

    def _via_candidates(self, o, d, base: Route, depart_at: datetime, kg: int, factors) -> list[list[Route]]:
        """
        Route through sideways via-points, all requests of one round at once.
        Returns one list of candidates per via-point, in `factors` order, so
        results are deterministic no matter which request finishes first.
        """
        midpoint = base.points[len(base.points) // 2]
        offset = via_offset_km(base)

        def one(factor: float) -> list[Route]:
            via = via_point(o, d, midpoint, offset * factor)
            try:
                return self.provider.calculate([o, via, d], depart_at, kg, 0)
            except ProviderError as exc:  # the via-point may land somewhere unroutable (e.g. a lake)
                logger.warning("via-point %.0f km failed: %s", offset * factor, type(exc).__name__)
                return []

        with ThreadPoolExecutor(max_workers=len(factors)) as pool:
            return list(pool.map(one, factors))
