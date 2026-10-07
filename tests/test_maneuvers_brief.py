"""Maneuver detection and the daily brief, on synthetic data."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import brief  # noqa: E402
import maneuvers  # noqa: E402


def es(nid, epoch, mm, mmdot=0.0):
    return {"NORAD_CAT_ID": nid, "EPOCH": epoch, "MEAN_MOTION": mm, "MEAN_MOTION_DOT": mmdot, "src": "active"}


class Maneuvers(unittest.TestCase):
    def test_drag_alone_is_not_a_maneuver(self):
        # Mean motion rising exactly as its derivative predicts: orbit decaying by drag.
        rows = [es(1, "2026-10-01T00:00:00", 15.20000, 0.0005), es(1, "2026-10-02T00:00:00", 15.20100, 0.0005),
                es(1, "2026-10-03T00:00:00", 15.20200, 0.0005)]
        seen, span = maneuvers.detect(rows)
        self.assertEqual(seen[1], 0)
        self.assertAlmostEqual(span, 2.0)

    def test_a_raise_is_a_maneuver(self):
        # Mean motion drops by 0.01 rev/day: semi-major axis up by about 3 km.
        rows = [es(2, "2026-10-01T00:00:00", 15.20), es(2, "2026-10-02T00:00:00", 15.19)]
        seen, _ = maneuvers.detect(rows)
        self.assertEqual(seen[2], 1)

    def test_long_gaps_are_ignored(self):
        rows = [es(3, "2026-10-01T00:00:00", 15.20), es(3, "2026-10-09T00:00:00", 15.10)]
        seen, _ = maneuvers.detect(rows)
        self.assertEqual(seen[3], 0)

    def test_needs_two_days(self):
        rows = [es(4, "2026-10-01T00:00:00", 15.2), es(4, "2026-10-01T12:00:00", 15.2)]
        self.assertIsNone(maneuvers.summarise(rows, [4], {}, lambda n: None, {}))


class Brief(unittest.TestCase):
    def test_brief_uses_only_given_numbers(self):
        s = {"totals": {"under_5km": 12290, "under_1km": 431},
             "stats": {"starlink": 11143, "others": 4502},
             "closest": [{"tca": "2026-10-07T13:01:28.384+00:00", "miss_km": 0.05, "vrel_kms": 13.87,
                          "starlink": {"name": "STARLINK-30376"},
                          "other": {"name": "CZ-2D R/B", "owner_name": "China", "type": "Rocket body"}}],
             "by_owner": [{"key": "PRC", "name": "China", "under_5km": 3512, "per_object": 2.77, "objects_screened": 1270},
                          {"key": "US", "name": "United States", "under_5km": 3032, "per_object": 2.67, "objects_screened": 1135},
                          {"key": "TBD", "name": "Unregistered", "under_5km": 719, "per_object": 6.48, "objects_screened": 111}],
             "dead_hardware": [{"name": "China", "total": 1069}, {"name": "Russia (CIS)", "total": 549}]}
        b = brief.build(s)
        self.assertIn("12,290", b["headline"])
        text = " ".join(b["lines"])
        for must in ("50 m", "13:01", "13.9 km/s", "3,512", "1,618", "6.48", "11,143"):
            self.assertIn(must, text + b["headline"])
        self.assertNotIn("—", text)
        self.assertNotIn("–", text)


if __name__ == "__main__":
    unittest.main()
