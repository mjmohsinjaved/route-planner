"""Shared HTTP plumbing for the provider adapters: one retry, and httpx errors turned into domain errors."""
import httpx

from ..domain.errors import ProviderError, ProviderTimeout, ProviderUnavailable


def translate(exc: httpx.HTTPError) -> ProviderError:
    """
    The domain error for an httpx failure. Never put str(exc) in the message:
    httpx includes the request URL, and with it the API key.
    """
    return ProviderTimeout() if isinstance(exc, httpx.TimeoutException) else ProviderUnavailable()


def get(url: str, *, params: dict, timeout: float, retries: int = 1) -> httpx.Response:
    """
    GET with a timeout and `retries` more tries on a network error or a 5xx.
    Returns the final response whatever its status; callers decide what a 4xx means.
    """
    for attempt in range(retries + 1):
        try:
            response = httpx.get(url, params=params, timeout=timeout)
        except httpx.TransportError as exc:
            if attempt == retries:
                raise translate(exc) from None
            continue
        if response.status_code >= 500 and attempt < retries:
            continue
        return response
    raise ProviderUnavailable()  # unreachable: the loop always returns or raises


def json_or_raise(response: httpx.Response):
    """The decoded body of a successful response; any error status becomes ProviderUnavailable."""
    try:
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise translate(exc) from None
    return response.json()
