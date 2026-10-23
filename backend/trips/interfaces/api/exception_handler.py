"""
DRF exception handler. Two jobs:

1. Map domain errors to HTTP statuses, so views stay free of try/except.
2. Give every error response a `detail` string. DRF's validation errors are
   keyed by field ({"departure": ["..."]}); the PRD (section 8) promises a
   `detail` message on every error so the UI can show one sentence without
   knowing the shape. Field messages are kept alongside it.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from ...domain.errors import (
    ForecastRateLimited,
    NoRouteFound,
    ProviderError,
    ProviderTimeout,
    TripNotFound,
)

RATE_LIMIT_RETRY_AFTER_SECONDS = 60  # Open-Meteo's allowance resets every minute


def first_message(data) -> str | None:
    """Depth-first search for the first human-readable message in a DRF error body."""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for value in data.values():
            found = first_message(value)
            if found:
                return found
    if isinstance(data, list):
        for value in data:
            found = first_message(value)
            if found:
                return found
    return None


def domain_error_response(exc: Exception) -> Response | None:
    """The response for a domain error, or None if `exc` is not one."""
    if isinstance(exc, TripNotFound):
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, NoRouteFound):
        return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    if isinstance(exc, ForecastRateLimited):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(RATE_LIMIT_RETRY_AFTER_SECONDS)},
        )
    if isinstance(exc, ProviderTimeout):
        return Response({"detail": str(exc)}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    if isinstance(exc, ProviderError):  # every ProviderError message is written for the UI
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    return None


def api_exception_handler(exc, context):
    domain_response = domain_error_response(exc)
    if domain_response is not None:
        return domain_response

    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(response.data, list):  # non-field errors raised as a top-level list
        response.data = {"non_field_errors": response.data}
    if isinstance(response.data, dict) and not isinstance(response.data.get("detail"), str):
        response.data["detail"] = first_message(response.data) or "Invalid request."
    return response
