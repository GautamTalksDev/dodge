"""Engine checks that do not need network or recorded data.

1. The spatial hash finds exactly the pairs a brute-force distance check
   finds (random clouds of points, many sizes, including cell edges).
2. The linear closest-approach estimate agrees with a fine brute-force SGP4
   sweep for real orbits from a crafted crossing.
3. The full screen finds a crafted near miss between two real-looking orbits.
"""
import math
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import screen  # noqa: E402


def brute_pairs(P, Q, okP, okQ, r):
    d = np.linalg.norm(P[:, None, :] - Q[None, :, :], axis=2)
    m = (d < r) & okP[:, None] & okQ[None, :]
    return set(zip(*np.nonzero(m)))


class SpatialHash(unittest.TestCase):
    def test_matches_brute_force(self):
        rng = np.random.default_rng(7)
        for n, spread in [(50, 400.0), (400, 2000.0), (800, 900.0), (300, 7000.0)]:
            P = rng.uniform(-spread, spread, (n, 3))
            Q = rng.uniform(-spread, spread, (n + 37, 3))
            # Put some points exactly on cell boundaries.
            Q[:20] = np.round(Q[:20] / screen.CELL_KM) * screen.CELL_KM
            okP = rng.random(n) > 0.05
            okQ = rng.random(n + 37) > 0.05
            I, J = screen.pairs_within(P, Q, okP, okQ)
            got = set(zip(I.tolist(), J.tolist()))
            self.assertEqual(got, brute_pairs(P, Q, okP, okQ, screen.CELL_KM), f"n={n} spread={spread}")


def omm(name, nid, epoch, inc, raan, mm, ma, ecc=0.0001, argp=0.0):
    return {"OBJECT_NAME": name, "OBJECT_ID": f"2026-001{chr(64 + nid % 26)}", "NORAD_CAT_ID": nid,
            "EPOCH": epoch.strftime("%Y-%m-%dT%H:%M:%S.%f"), "MEAN_MOTION": mm, "ECCENTRICITY": ecc,
            "INCLINATION": inc, "RA_OF_ASC_NODE": raan, "ARG_OF_PERICENTER": argp, "MEAN_ANOMALY": ma,
            "BSTAR": 0.0001, "MEAN_MOTION_DOT": 0.0, "MEAN_MOTION_DDOT": 0.0, "EPHEMERIS_TYPE": 0,
            "CLASSIFICATION_TYPE": "U", "ELEMENT_SET_NO": 999, "REV_AT_EPOCH": 1, "src": "test"}


class NearMiss(unittest.TestCase):
    def test_crafted_crossing_is_found_and_refined(self):
        t0 = datetime(2026, 10, 6, 0, 0, tzinfo=timezone.utc)
        mm = 15.06  # about 550 km
        a = omm("STAR", 90001, t0, 53.0, 10.0, mm, 0.0)
        # Same altitude, different plane, both start at the shared ascending
        # node direction offset; search for the phase that gives a close pass.
        sa = screen.satrec(a)
        best = None
        for ma in np.arange(0.0, 360.0, 0.25):
            b = omm("OTHER", 90002, t0, 97.5, 10.0, mm, float(ma))
            sb = screen.satrec(b)
            ts = [t0 + timedelta(seconds=s) for s in range(0, 6000, 5)]
            jd, fr = screen.jdfr(ts)
            _, ra, _ = sa.sgp4_array(jd, fr)
            _, rb, _ = sb.sgp4_array(jd, fr)
            d = np.linalg.norm(ra - rb, axis=1)
            k = int(np.argmin(d))
            if best is None or d[k] < best[0]:
                best = (float(d[k]), float(ma), ts[k])
        self.assertLess(best[0], 20.0)
        b = omm("OTHER", 90002, t0, 97.5, 10.0, mm, best[1])
        old = screen.REFINE_KM, screen.REPORT_KM
        screen.REFINE_KM = screen.REPORT_KM = 25.0
        try:
            events, stats, screened = screen.screen([a], [b], t0, 2.0)
        finally:
            screen.REFINE_KM, screen.REPORT_KM = old
        self.assertTrue(events, "crafted near miss not found")
        e = events[0]
        # Brute force at 20 ms around the reported time must not beat it.
        sb = screen.satrec(b)
        ts = [e["tca"] + timedelta(seconds=s) for s in np.arange(-3, 3, 0.02)]
        jd, fr = screen.jdfr(ts)
        _, ra, _ = sa.sgp4_array(jd, fr)
        _, rb, _ = sb.sgp4_array(jd, fr)
        self.assertGreaterEqual(float(np.min(np.linalg.norm(ra - rb, axis=1))) + 1e-3, e["miss_km"] - 0.05)
        self.assertLess(abs(e["miss_km"] - e["est_km"]), 0.2, "linear estimate disagrees with SGP4 refinement")


if __name__ == "__main__":
    unittest.main()
