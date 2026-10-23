from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from trips.domain.entities import Checkpoint
from trips.domain.errors import ForecastMissing
from trips.domain.forecast import Reading, checkpoint_window, conditions_at, precip_hour, round_coord, wind_hour

from ..fakes import utc


class ForecastHourTests(SimpleTestCase):
    def test_precip_uses_end_of_hour_value(self):
        # Rain/snowfall are totals for the preceding hour: 15:00 covers 14:00-15:00
        self.assertEqual(precip_hour(utc(14, 20)), utc(15))
        self.assertEqual(precip_hour(utc(14, 0)), utc(15))
        self.assertEqual(precip_hour(utc(14, 59)), utc(15))

    def test_wind_uses_nearest_hour(self):
        self.assertEqual(wind_hour(utc(14, 29)), utc(14))
        self.assertEqual(wind_hour(utc(14, 30)), utc(15))

    def test_other_timezones_convert_to_utc(self):
        karachi = timezone(timedelta(hours=5))
        self.assertEqual(precip_hour(datetime(2026, 10, 21, 19, 20, tzinfo=karachi)), utc(15))

    def test_coordinates_round_to_a_tenth_of_a_degree(self):
        self.assertEqual(round_coord(41.04, -87.04), (41.0, -87.0))
        self.assertEqual(round_coord(41.06, -87.06), (41.1, -87.1))


class ConditionsAtTests(SimpleTestCase):
    def test_reads_wind_at_the_nearest_hour_and_rain_at_the_next_stamp(self):
        series = {
            int(utc(14).timestamp()): Reading(wind_mph=20, gust_mph=30, rain_in=0.0, snow_in=0.0),
            int(utc(15).timestamp()): Reading(wind_mph=30, gust_mph=40, rain_in=0.1, snow_in=0.2),
        }
        c = conditions_at(series, utc(14, 20))
        self.assertEqual((c.wind_mph, c.gust_mph), (20, 30))  # wind at 14:00
        self.assertEqual((c.rain_in_hr, c.snow_in_hr), (0.1, 0.2))  # precipitation at 15:00

    def test_missing_hour_is_an_error(self):
        series = {int(utc(14).timestamp()): Reading(10, 12, 0, 0)}
        with self.assertRaises(ForecastMissing):
            conditions_at(series, utc(14, 0))  # needs the 15:00 precipitation stamp too

    def test_missing_values_are_an_error_not_calm(self):
        # A null from the provider must never score as Low: the trip is refused instead.
        for wind, rain, snow in ((None, 0.0, 0.0), (10, None, 0.0), (10, 0.0, None)):
            with self.subTest(wind=wind, rain=rain, snow=snow):
                reading = Reading(wind_mph=wind, gust_mph=12, rain_in=rain, snow_in=snow)
                series = {int(utc(14).timestamp()): reading, int(utc(15).timestamp()): reading}
                with self.assertRaises(ForecastMissing):
                    conditions_at(series, utc(14, 0))

    def test_missing_gust_is_allowed(self):
        # Gusts are shown for context only, so a missing gust does not block the trip
        reading = Reading(wind_mph=10, gust_mph=None, rain_in=0.0, snow_in=0.0)
        series = {int(utc(14).timestamp()): reading, int(utc(15).timestamp()): reading}
        c = conditions_at(series, utc(14, 0))
        self.assertEqual(c.wind_mph, 10)
        self.assertIsNone(c.gust_mph)

    def test_values_are_returned_unrounded(self):
        # Classification happens on the raw value: 24.96 mph is Low, where a rounded 25.0 would be Moderate
        reading = Reading(wind_mph=24.96, gust_mph=30.04, rain_in=0.2496, snow_in=0)
        series = {int(utc(h).timestamp()): reading for h in (14, 15)}
        c = conditions_at(series, utc(14, 0))
        self.assertEqual(c.wind_mph, 24.96)
        self.assertEqual(c.rain_in_hr, 0.2496)


class CheckpointWindowTests(SimpleTestCase):
    def test_spans_first_wind_hour_to_last_precip_stamp(self):
        cps = [Checkpoint(i, 0, 0, 0, 0, eta) for i, eta in enumerate((utc(14, 20), utc(16, 10)))]
        self.assertEqual(checkpoint_window(cps), (utc(14), utc(17)))
