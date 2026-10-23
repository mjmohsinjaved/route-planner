from datetime import datetime, timedelta, timezone
from unittest import mock

import httpx
from django.test import SimpleTestCase

from trips.domain.errors import ForecastRateLimited, ProviderTimeout, ProviderUnavailable
from trips.domain.forecast import Reading
from trips.infrastructure import http, openmeteo_forecast
from trips.infrastructure.openmeteo_forecast import OpenMeteoForecast, cache_key

from ..fakes import InMemoryCache, utc


def fake_location(start: datetime, hours: int, wind: list, rain: list):
    times = [int((start + timedelta(hours=i)).timestamp()) for i in range(hours)]
    return {
        "hourly": {
            "time": times,
            "wind_speed_10m": wind,
            "wind_gusts_10m": [None if w is None else w + 10 for w in wind],
            "rain": rain,
            "snowfall": [0.0] * hours,
        }
    }


def epoch(t: datetime) -> int:
    return int(t.timestamp())


class HourlyTests(SimpleTestCase):
    def setUp(self):
        self.cache = InMemoryCache()
        self.forecast = OpenMeteoForecast(self.cache)

    def test_batches_points_into_one_request_and_parses_readings(self):
        coords = [(41.0, -87.0), (42.0, -90.0)]
        loc = fake_location(utc(14), 4, wind=[20, 30, 40, 50], rain=[0.0, 0.1, 0.2, 0.3])
        with mock.patch.object(openmeteo_forecast, "_get", return_value=[loc, loc]) as get:
            result = self.forecast.hourly(coords, utc(14), utc(17))

        get.assert_called_once()  # one request for both cells
        params = get.call_args.args[0]
        self.assertEqual(params["latitude"], "41.0,42.0")
        self.assertEqual(params["longitude"], "-87.0,-90.0")
        self.assertEqual(params["wind_speed_unit"], "mph")
        self.assertEqual(params["precipitation_unit"], "inch")
        self.assertEqual(params["timezone"], "GMT")
        self.assertEqual(params["start_hour"], "2026-10-21T14:00")
        self.assertEqual(params["end_hour"], "2026-10-21T17:00")

        self.assertEqual(result[(41.0, -87.0)][epoch(utc(15))], Reading(wind_mph=30, gust_mph=40, rain_in=0.1, snow_in=0.0))

    def test_second_lookup_uses_cache(self):
        loc = fake_location(utc(14), 2, wind=[20, 30], rain=[0.0, 0.1])
        with mock.patch.object(openmeteo_forecast, "_get", return_value=[loc]) as get:
            self.forecast.hourly([(41.0, -87.0)], utc(14), utc(15))
            self.forecast.hourly([(41.0, -87.0)], utc(14), utc(15))
        get.assert_called_once()

    def test_a_missing_value_comes_back_as_none_not_zero(self):
        loc = fake_location(utc(14), 2, wind=[None, 10], rain=[0.0, None])
        loc["hourly"]["wind_gusts_10m"] = [None, None]
        with mock.patch.object(openmeteo_forecast, "_get", return_value=[loc]):
            series = self.forecast.hourly([(41.0, -87.0)], utc(14), utc(15))[(41.0, -87.0)]
        self.assertEqual(series[epoch(utc(14))], Reading(None, None, 0.0, 0.0))
        self.assertEqual(series[epoch(utc(15))], Reading(10, None, None, 0.0))

    def test_a_response_with_the_wrong_number_of_locations_is_an_error(self):
        loc = fake_location(utc(14), 2, wind=[1, 2], rain=[0, 0])
        with mock.patch.object(openmeteo_forecast, "_get", return_value=[loc]):
            with self.assertRaises(ProviderUnavailable):
                self.forecast.hourly([(41.0, -87.0), (42.0, -90.0)], utc(14), utc(15))


class FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else []

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError("raise_for_status should not be reached in these tests")


PARAMS = {"latitude": "41.0", "longitude": "-87.0"}


class RateLimitTests(SimpleTestCase):
    @mock.patch.object(http.httpx, "get")
    def test_429_fails_at_once_with_a_clear_message(self, get):
        get.return_value = FakeResponse(429)
        with self.assertRaises(ForecastRateLimited) as ctx:
            openmeteo_forecast._get(PARAMS)
        self.assertEqual(str(ctx.exception), openmeteo_forecast.RATE_LIMIT_MESSAGE)
        get.assert_called_once()  # the allowance resets per minute; retrying would only burn calls

    @mock.patch.object(http.httpx, "get")
    def test_5xx_then_200_succeeds(self, get):
        get.side_effect = [FakeResponse(503), FakeResponse(200, [{"hourly": {}}])]
        self.assertEqual(openmeteo_forecast._get(PARAMS), [{"hourly": {}}])
        self.assertEqual(get.call_count, 2)

    @mock.patch.object(http.httpx, "get")
    def test_a_single_location_response_is_wrapped_in_a_list(self, get):
        get.return_value = FakeResponse(200, {"hourly": {}})
        self.assertEqual(openmeteo_forecast._get(PARAMS), [{"hourly": {}}])

    @mock.patch.object(http.httpx, "get", side_effect=httpx.ReadTimeout("slow"))
    def test_a_timeout_is_a_provider_timeout(self, get):
        with self.assertRaises(ProviderTimeout):
            openmeteo_forecast._get(PARAMS)


class ChunkCachingTests(SimpleTestCase):
    def setUp(self):
        self.cache = InMemoryCache()
        self.forecast = OpenMeteoForecast(self.cache)

    @mock.patch.object(openmeteo_forecast, "CHUNK_SIZE", 1)
    def test_successful_chunks_are_cached_when_another_chunk_fails(self):
        good, bad = (41.0, -87.0), (42.0, -90.0)

        def get(params):
            if params["latitude"] == "42.0":
                raise ForecastRateLimited(openmeteo_forecast.RATE_LIMIT_MESSAGE)
            return [fake_location(utc(14), 2, wind=[20, 30], rain=[0.0, 0.1])]

        with mock.patch.object(openmeteo_forecast, "_get", side_effect=get):
            with self.assertRaises(ForecastRateLimited):
                self.forecast.hourly([good, bad], utc(14), utc(15))

        self.assertIsNotNone(self.cache.get(cache_key(good)))  # kept, so a retry only refetches `bad`
        self.assertIsNone(self.cache.get(cache_key(bad)))

        with mock.patch.object(openmeteo_forecast, "_get", side_effect=get) as get_again:
            with self.assertRaises(ForecastRateLimited):
                self.forecast.hourly([good, bad], utc(14), utc(15))
        self.assertEqual(get_again.call_count, 1)  # only the failed coordinate goes out again

    def test_narrow_fetch_merges_into_the_cached_series(self):
        coord = (41.0, -87.0)
        wide = fake_location(utc(14), 6, wind=[10] * 6, rain=[0.0] * 6)
        with mock.patch.object(openmeteo_forecast, "_get", return_value=[wide]):
            self.forecast.hourly([coord], utc(14), utc(19))

        narrow = fake_location(utc(22), 2, wind=[50, 55], rain=[0.0, 0.0])
        with mock.patch.object(openmeteo_forecast, "_get", return_value=[narrow]):
            self.forecast.hourly([coord], utc(22), utc(23))

        series = self.cache.get(cache_key(coord))
        stamps = {datetime.fromtimestamp(s, timezone.utc) for s in series}
        self.assertEqual(stamps, {utc(14) + timedelta(hours=i) for i in range(6)} | {utc(22), utc(23)})

        with mock.patch.object(openmeteo_forecast, "_get") as get:  # the wide range is still a cache hit
            self.forecast.hourly([coord], utc(14), utc(19))
        get.assert_not_called()
