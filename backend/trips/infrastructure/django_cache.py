"""CachePort over Django's cache framework (local memory today; Redis is a settings change)."""
from typing import Callable, Sequence

from django.core.cache import cache


class DjangoCache:
    def get(self, key: str):
        return cache.get(key)

    def set(self, key: str, value, ttl_seconds: int) -> None:
        cache.set(key, value, ttl_seconds)

    def get_many(self, keys: Sequence[str]) -> dict:
        return cache.get_many(list(keys))

    def set_many(self, items: dict, ttl_seconds: int) -> None:
        cache.set_many(items, ttl_seconds)

    def get_or_set(self, key: str, make: Callable[[], object], ttl_seconds: int):
        return cache.get_or_set(key, make, ttl_seconds)
