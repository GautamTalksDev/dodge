#!/usr/bin/env python3
"""Recall check on real recorded data: does the fast screen miss anything?

Takes a random sample of Starlinks and of the other screened objects, finds
every approach under REPORT_KM by brute force (all pairs, 1 s steps, then
0.05 s refinement), runs the fast screen on the same sample, and compares.

    python tests/check_recall.py work/gp-2026-10-06.ndjson.gz --hours 3
"""
import argparse
import os
import random
import sys
from datetime import timedelta

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import screen  # noqa: E402


def brute(star, others, t0, hours):
    A, sa, star, _ = screen.build(star)
    B, sb, others, _ = screen.build(others)
    found = {}
    step = 1.0
    n = int(hours * 3600 / step)
    for c0 in range(0, n, 600):
        ts = [t0 + timedelta(seconds=(c0 + k) * step) for k in range(min(600, n - c0))]
        jd, fr = screen.jdfr(ts)
        ea, ra, _ = A.sgp4(jd, fr)
        eb, rb, _ = B.sgp4(jd, fr)
        for i in range(len(star)):
            d = np.linalg.norm(ra[i][None, :, :] - rb, axis=2)  # (others, times)
            d[(eb != 0) | (ea[i][None, :] != 0)] = np.inf
            js, ks = np.nonzero(d < 25.0)
            for j, k in zip(js, ks):
                key = (i, int(j), int((c0 + k) * step // 600))
                if key not in found or d[j, k] < found[key][0]:
                    found[key] = (float(d[j, k]), ts[k])
    out = set()
    for (i, j, _), (_, t) in found.items():
        tt, km, _ = screen.refine(sa[i], sb[j], t)
        if km <= screen.REPORT_KM:
            out.add((star[i]["NORAD_CAT_ID"], others[j]["NORAD_CAT_ID"], tt.replace(microsecond=0).isoformat()[:15]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--hours", type=float, default=3)
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rows = screen.load_rows(a.files)
    # Start at the newest Starlink (SupGP) epoch: public sets can carry epochs
    # days ahead (a few rocket bodies do), which would make everything stale.
    t0 = max(screen.parse_epoch(r["EPOCH"]) for r in rows if r["src"] == "starlink-supgp")
    t0 = t0.replace(minute=0, second=0, microsecond=0)
    star, others, _, _ = screen.select(rows, t0)
    rnd = random.Random(a.seed)
    star = rnd.sample(star, min(a.n, len(star)))
    others = rnd.sample(others, min(a.n, len(others)))
    ref = brute(star, others, t0, a.hours)
    events, _, _ = screen.screen(star, others, t0, a.hours)
    got = {(e["starlink"]["NORAD_CAT_ID"], e["other"]["NORAD_CAT_ID"], e["tca"].replace(microsecond=0).isoformat()[:15]) for e in events}
    missed = ref - {g for g in got}
    # Same pair within the same 10 minutes counts as the same encounter.
    def loose(s):
        return {(x, y, t[:14]) for x, y, t in s}
    missed = loose(ref) - loose(got)
    print(f"brute force: {len(ref)} approaches under {screen.REPORT_KM} km; fast screen: {len(got)}; missed: {len(missed)}")
    for m in sorted(missed)[:10]:
        print("  missed", m)
    sys.exit(1 if missed else 0)


if __name__ == "__main__":
    main()
