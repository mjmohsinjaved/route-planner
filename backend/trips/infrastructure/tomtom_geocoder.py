"""GeocoderPort over the TomTom Search API."""
from urllib.parse import quote

from django.conf import settings

from ..domain.entities import Place
from ..domain.errors import GeocodingUnavailable, ProviderError
from . import http

SEARCH_URL = "https://api.tomtom.com/search/2/search/{query}.json"
TIMEOUT_SECONDS = 10


class TomTomGeocoder:
    def search(self, query: str, limit: int) -> list[Place]:
        try:
            response = http.get(
                # safe="" encodes "/" too, so the query is always one path segment and "../" cannot retarget the request
                SEARCH_URL.format(query=quote(query, safe="")),
                params={
                    "key": settings.TOMTOM_API_KEY,
                    "limit": limit,
                    "typeahead": "true",
                    "countrySet": "US,CA",
                },
                timeout=TIMEOUT_SECONDS,
                retries=0,  # the user can type again
            )
            body = http.json_or_raise(response)
        except ProviderError:
            raise GeocodingUnavailable() from None
        return [
            Place(
                name=item["address"].get("freeformAddress", query),
                lat=item["position"]["lat"],
                lon=item["position"]["lon"],
            )
            for item in body.get("results", [])
        ]
