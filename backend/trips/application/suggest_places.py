"""Place suggestions for the autocomplete."""
from ..domain.entities import Place
from .ports import CachePort, GeocoderPort

CACHE_SECONDS = 60 * 60 * 24  # 24 hours
MIN_QUERY_LENGTH = 2


class SuggestPlaces:
    def __init__(self, geocoder: GeocoderPort, cache: CachePort):
        self.geocoder = geocoder
        self.cache = cache

    def __call__(self, query: str, limit: int = 5) -> list[Place]:
        """Up to `limit` places for the text; nothing for text shorter than 2 characters."""
        query = query.strip()
        if len(query) < MIN_QUERY_LENGTH:
            return []
        key = f"geocode:{query.lower()}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        places = self.geocoder.search(query, limit)
        self.cache.set(key, places, CACHE_SECONDS)
        return places
