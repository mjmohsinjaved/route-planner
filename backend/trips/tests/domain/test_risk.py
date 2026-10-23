from django.test import SimpleTestCase

from trips.domain.entities import Risk
from trips.domain.risk import (
    HIGH,
    LOW,
    MODERATE,
    NO_TRAVEL,
    SEVERE,
    classify,
    level_score,
    load_level,
    rain_level,
    snow_level,
    wind_level,
)


class WindThresholdTests(SimpleTestCase):
    def test_edges(self):
        cases = [
            (0, LOW), (24.9, LOW), (25, MODERATE), (34.9, MODERATE),
            (35, HIGH), (44.9, HIGH), (45, SEVERE), (54.9, SEVERE),
            (55, NO_TRAVEL), (80, NO_TRAVEL),
        ]
        for mph, expected in cases:
            with self.subTest(mph=mph):
                self.assertEqual(wind_level(mph), expected)


class RainThresholdTests(SimpleTestCase):
    def test_edges(self):
        cases = [
            (0, LOW), (0.09, LOW), (0.10, MODERATE), (0.24, MODERATE),
            (0.25, HIGH), (0.49, HIGH), (0.50, SEVERE), (1.00, SEVERE),
            (1.01, NO_TRAVEL),
        ]
        for rain, expected in cases:
            with self.subTest(rain=rain):
                self.assertEqual(rain_level(rain), expected)


class SnowThresholdTests(SimpleTestCase):
    def test_edges(self):
        cases = [
            (0, LOW), (0.49, LOW), (0.5, MODERATE), (0.99, MODERATE),
            (1.0, HIGH), (1.99, HIGH), (2.0, SEVERE), (3.0, SEVERE),
            (3.01, NO_TRAVEL),
        ]
        for snow, expected in cases:
            with self.subTest(snow=snow):
                self.assertEqual(snow_level(snow), expected)


class LoadRuleTests(SimpleTestCase):
    def test_55_mph_is_no_travel_for_any_load(self):
        for load in (1, 10_000, 80_000):
            with self.subTest(load=load):
                self.assertEqual(load_level(55, load), NO_TRAVEL)

    def test_45_to_54_mph_over_30000_lb_is_no_travel(self):
        self.assertEqual(load_level(45, 30_001), NO_TRAVEL)
        self.assertEqual(load_level(54.9, 45_000), NO_TRAVEL)

    def test_45_to_54_mph_at_exactly_30000_lb_does_not_trigger(self):
        self.assertEqual(load_level(50, 30_000), LOW)

    def test_35_to_44_mph_over_40000_lb_is_severe(self):
        self.assertEqual(load_level(35, 40_001), SEVERE)
        self.assertEqual(load_level(44.9, 50_000), SEVERE)

    def test_35_to_44_mph_at_exactly_40000_lb_does_not_trigger(self):
        self.assertEqual(load_level(40, 40_000), LOW)

    def test_below_35_mph_no_load_rule(self):
        self.assertEqual(load_level(34.9, 80_000), LOW)


class ClassifyTests(SimpleTestCase):
    def test_all_low(self):
        result = classify(10, 0.01, 0, 38_000)
        self.assertEqual(result, Risk("Low", LOW, "All conditions Low"))

    def test_worst_condition_wins(self):
        result = classify(26, 0.30, 0.6, 10_000)  # Moderate wind, High rain, Moderate snow
        self.assertEqual(result.level, "High")
        self.assertEqual(result.reason, "Rain 0.3 in/hr → High")

    def test_load_raises_severe_wind_to_no_travel(self):
        result = classify(47, 0, 0, 38_000)
        self.assertEqual(result.level, "No Travel")
        self.assertEqual(result.reason, "Wind 47.0 mph + 38,000 lb load → No Travel")

    def test_load_raises_high_wind_to_severe(self):
        result = classify(40, 0, 0, 42_000)
        self.assertEqual(result.level, "Severe")
        self.assertIn("42,000 lb load", result.reason)

    def test_light_load_keeps_plain_wind_level(self):
        result = classify(47, 0, 0, 20_000)
        self.assertEqual(result.level, "Severe")
        self.assertEqual(result.reason, "Wind 47.0 mph → Severe")

    def test_ties_name_every_cause(self):
        result = classify(36, 0.30, 0, 10_000)  # High wind and High rain
        self.assertEqual(result.reason, "Wind 36.0 mph; Rain 0.3 in/hr → High")


class LevelScoreTests(SimpleTestCase):
    def test_matches_classify_across_the_rule_edges(self):
        for wind in (0, 25, 35, 45, 47, 55):
            for rain in (0, 0.1, 0.25, 0.5, 1.01):
                for snow in (0, 0.5, 1.0, 2.0, 3.01):
                    for load in (20_000, 38_000, 42_000):
                        with self.subTest(wind=wind, rain=rain, snow=snow, load=load):
                            self.assertEqual(level_score(wind, rain, snow, load), classify(wind, rain, snow, load).level_score)
