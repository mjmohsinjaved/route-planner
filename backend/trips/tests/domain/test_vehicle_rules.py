from django.test import SimpleTestCase

from trips.domain.entities import Route
from trips.domain.vehicle_rules import TARGET_ROUTES, add_distinct, is_duplicate, via_offset_km, vehicle_weight_kg


def route(length_m, time_s):
    return Route(id="", distance_m=length_m, duration_s=time_s, points=[], time_anchors=[])


class VehicleWeightTests(SimpleTestCase):
    def test_adds_the_tractor_trailer_tare_and_converts_to_kg(self):
        self.assertEqual(vehicle_weight_kg(38_000), round(73_000 * 0.45359237))

    def test_heavier_load_is_heavier_vehicle(self):
        self.assertGreater(vehicle_weight_kg(45_000), vehicle_weight_kg(25_000))


class DuplicateTests(SimpleTestCase):
    def test_within_one_percent_on_both_is_a_duplicate(self):
        self.assertTrue(is_duplicate(route(100_500, 3_620), [route(100_000, 3_600)]))

    def test_different_distance_or_time_is_distinct(self):
        base = [route(100_000, 3_600)]
        self.assertFalse(is_duplicate(route(105_000, 3_600), base))
        self.assertFalse(is_duplicate(route(100_000, 3_800), base))

    def test_add_distinct_skips_duplicates_and_stops_at_three(self):
        routes = [route(100_000, 3_600)]
        add_distinct(routes, [route(100_100, 3_601), route(110_000, 4_000), route(120_000, 4_400), route(130_000, 5_000)])
        self.assertEqual(len(routes), TARGET_ROUTES)
        self.assertEqual([r.distance_m for r in routes], [100_000, 110_000, 120_000])


class ViaOffsetTests(SimpleTestCase):
    def test_ten_percent_of_the_length_clamped_to_30_to_80_km(self):
        self.assertEqual(via_offset_km(route(100_000, 1)), 30)  # 10 km -> floor
        self.assertEqual(via_offset_km(route(500_000, 1)), 50)
        self.assertEqual(via_offset_km(route(1_600_000, 1)), 80)  # 160 km -> cap
