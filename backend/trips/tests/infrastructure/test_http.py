from unittest import mock

import httpx
from django.test import SimpleTestCase

from trips.domain.errors import ProviderTimeout, ProviderUnavailable
from trips.infrastructure import http

URL = "https://example.test/route"
SECRET_PARAMS = {"key": "super-secret-key"}


class GetTests(SimpleTestCase):
    @mock.patch.object(http.httpx, "get")
    def test_retries_once_on_a_5xx_and_returns_the_second_response(self, get):
        get.side_effect = [httpx.Response(503), httpx.Response(200, json={"ok": True})]
        response = http.get(URL, params={}, timeout=5)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get.call_count, 2)

    @mock.patch.object(http.httpx, "get")
    def test_a_4xx_is_returned_not_retried(self, get):
        get.return_value = httpx.Response(429)
        self.assertEqual(http.get(URL, params={}, timeout=5).status_code, 429)
        get.assert_called_once()

    @mock.patch.object(http.httpx, "get")
    def test_no_retries_when_asked(self, get):
        get.return_value = httpx.Response(503)
        self.assertEqual(http.get(URL, params={}, timeout=5, retries=0).status_code, 503)
        get.assert_called_once()

    @mock.patch.object(http.httpx, "get", side_effect=httpx.ReadTimeout("slow"))
    def test_timeouts_become_provider_timeout_after_one_retry(self, get):
        with self.assertRaises(ProviderTimeout):
            http.get(URL, params={}, timeout=5)
        self.assertEqual(get.call_count, 2)

    @mock.patch.object(http.httpx, "get", side_effect=httpx.ConnectError("down"))
    def test_network_errors_become_provider_unavailable(self, get):
        with self.assertRaises(ProviderUnavailable):
            http.get(URL, params={}, timeout=5)

    def test_error_messages_never_carry_the_url_or_key(self):
        request = httpx.Request("GET", URL, params=SECRET_PARAMS)
        with mock.patch.object(http.httpx, "get", side_effect=httpx.ConnectError("down", request=request)):
            with self.assertRaises(ProviderUnavailable) as ctx:
                http.get(URL, params=SECRET_PARAMS, timeout=5)
        self.assertNotIn("super-secret-key", str(ctx.exception))
        self.assertNotIn("example.test", str(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)  # the httpx error, which holds the URL, is not chained


class JsonOrRaiseTests(SimpleTestCase):
    def test_returns_the_body_of_a_success(self):
        response = httpx.Response(200, json={"a": 1}, request=httpx.Request("GET", URL))
        self.assertEqual(http.json_or_raise(response), {"a": 1})

    def test_an_error_status_becomes_provider_unavailable(self):
        response = httpx.Response(404, request=httpx.Request("GET", URL, params=SECRET_PARAMS))
        with self.assertRaises(ProviderUnavailable) as ctx:
            http.json_or_raise(response)
        self.assertNotIn("super-secret-key", str(ctx.exception))
