"""
Errors the domain and application layers raise. The interface layer maps each
to an HTTP status (interfaces/api/exception_handler.py); adapters translate
their library's errors into these, so nothing above infrastructure sees httpx.

Messages are safe to show to a user: they never carry URLs or API keys.
"""


class DomainError(Exception):
    pass


class TripNotFound(DomainError):
    pass


class NoRouteFound(DomainError):
    """The routing provider found no truck route between the places."""


class ProviderError(DomainError):
    """A third-party service failed. `str(exc)` is a sentence for the UI."""


class ProviderUnavailable(ProviderError):
    def __init__(self, message: str = "A routing or weather service failed. Try again."):
        super().__init__(message)


class ProviderTimeout(ProviderError):
    def __init__(self, message: str = "A routing or weather service took too long. Try again."):
        super().__init__(message)


class GeocodingUnavailable(ProviderError):
    def __init__(self, message: str = "Geocoding service is unavailable. Try again."):
        super().__init__(message)


class ForecastMissing(ProviderError):
    """The forecast has no value for a checkpoint hour. Unknown weather is never read as calm."""


class ForecastRateLimited(ProviderError):
    """The weather provider's per-minute allowance is used up."""
