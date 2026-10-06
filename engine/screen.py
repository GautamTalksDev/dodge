#!/usr/bin/env python3
"""DODGE screening: close approaches between Starlink and everything else.

Inputs are the recorder's day files: Starlink from SupGP (SpaceX's own
ephemerides, refit by CelesTrak) and every other object from public GP data.

Method (screening grade, not collision probability):
1. Latest element set per object; drop stale sets (older than MAX_AGE_DAYS)
   and objects whose perigee/apogee never reach the Starlink band.
2. Propagate everything with SGP4 (Vallado's reference code) on a 10 s grid.
3. At each step, a spatial hash with 100 km cells finds every
   Starlink-to-other pair closer than 100 km.
4. For each such sample, a linear relative-motion estimate gives the time and
   distance of closest approach within that step. Relative acceleration
   between two objects 100 km apart is under 0.1 m/s^2, so the linear error
   over 5 s is about a metre.
5. Approaches estimated under REFINE_KM are re-propagated at 50 ms around the
   minimum for the final miss distance.
"""
import gzip
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np
from sgp4 import omm
from sgp4.api import Satrec, SatrecArray, jday

MU = 398600.4418  # km^3/s^2
RE = 6378.137
STEP_S = 10.0
CELL_KM = 100.0
REFINE_KM = 10.0
REPORT_KM = 5.0
MAX_AGE_DAYS = 7.0
BAND_MARGIN_KM = 25.0


def parse_epoch(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def perigee_apogee(o):
    n = float(o["MEAN_MOTION"]) * 2 * math.pi / 86400.0
    a = (MU / n ** 2) ** (1 / 3)
    e = float(o["ECCENTRICITY"])
    return a * (1 - e) - RE, a * (1 + e) - RE


def satrec(o):
    s = Satrec()
    fields = {k: str(v) for k, v in o.items() if v is not None}
    fields.setdefault("MEAN_MOTION_DDOT", "0")
    omm.initialize(s, fields)
    return s


def latest(rows):
    """Best element set per (source kind, NORAD id).

    Operator ephemerides (SupGP, src "supgp-*") beat public radar-based sets
    for the same object; within a kind the newest epoch wins.
    """
    best = {}
    for r in rows:
        k = ("star" if r["src"] == "starlink-supgp" else "other", r["NORAD_CAT_ID"])
        rank = (r["src"].startswith("supgp-"), r["EPOCH"])
        if k not in best or rank > (best[k]["src"].startswith("supgp-"), best[k]["EPOCH"]):
            best[k] = r
    return best


def load_rows(paths):
    rows = []
    for p in paths:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            rows.extend(json.loads(line) for line in f)
    return rows


def select(rows, t0):
    best = latest(rows)
    star = [r for (kind, _), r in best.items() if kind == "star"]
    star_ids = {r["NORAD_CAT_ID"] for r in star}
    lo = min(perigee_apogee(r)[0] for r in star) - BAND_MARGIN_KM
    hi = max(perigee_apogee(r)[1] for r in star) + BAND_MARGIN_KM
    others, dropped = [], defaultdict(int)
    for (kind, nid), r in best.items():
        if kind != "other":
            continue
        if nid in star_ids or str(r.get("OBJECT_NAME", "")).startswith("STARLINK"):
            dropped["starlink_public_set"] += 1  # SpaceX coordinates its own fleet
            continue
        age = (t0 - parse_epoch(r["EPOCH"])).total_seconds() / 86400
        if age > MAX_AGE_DAYS:
            dropped["stale"] += 1
            continue
        p, a = perigee_apogee(r)
        if a < lo or p > hi:
            dropped["outside_band"] += 1
            continue
        others.append(r)
    star = [r for r in star if (t0 - parse_epoch(r["EPOCH"])).total_seconds() / 86400 <= MAX_AGE_DAYS]
    return star, others, dict(dropped), (lo, hi)


def build(objs):
    sats, keep, bad = [], [], 0
    for o in objs:
        try:
            sats.append(satrec(o))
            keep.append(o)
        except Exception:
            bad += 1
    return SatrecArray(sats), sats, keep, bad


def cell_keys(cells):
    off, m = 256, 512
    return ((cells[:, 0] + off) * m + (cells[:, 1] + off)) * m + (cells[:, 2] + off)


OFFSETS = np.array([(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)], dtype=np.int64)


def pairs_within(P, Q, okP, okQ):
    """Indices (i, j) with |P[i]-Q[j]| < CELL_KM, using a 100 km spatial hash."""
    qi = np.nonzero(okQ)[0]
    if not len(qi):
        return np.empty(0, int), np.empty(0, int)
    cq = np.floor(Q[qi] / CELL_KM).astype(np.int64)
    kq = cell_keys(cq)
    order = np.argsort(kq, kind="stable")
    sk = kq[order]
    pi = np.nonzero(okP)[0]
    cp = np.floor(P[pi] / CELL_KM).astype(np.int64)
    I, J = [], []
    for d in OFFSETS:
        kp = cell_keys(cp + d)
        lo = np.searchsorted(sk, kp, "left")
        hi = np.searchsorted(sk, kp, "right")
        cnt = hi - lo
        tot = int(cnt.sum())
        if not tot:
            continue
        starts = np.repeat(lo, cnt)
        within = np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        I.append(np.repeat(pi, cnt))
        J.append(qi[order[starts + within]])
    if not I:
        return np.empty(0, int), np.empty(0, int)
    I, J = np.concatenate(I), np.concatenate(J)
    d = np.linalg.norm(P[I] - Q[J], axis=1)
    m = d < CELL_KM
    return I[m], J[m]


def jdfr(ts):
    """Julian date split into whole and fraction arrays, as SGP4 wants."""
    pairs = np.array([jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6) for t in ts])
    return pairs[:, 0].copy(), pairs[:, 1].copy()


def refine(a, b, t_center):
    """Exact SGP4 minimum within +-6 s of t_center (datetime). Returns (t, km, km/s)."""
    secs = np.arange(-6.0, 6.0001, 0.05)
    ts = [t_center + timedelta(seconds=float(s)) for s in secs]
    jd, fr = jdfr(ts)
    ea, ra, va = a.sgp4_array(jd, fr)
    eb, rb, vb = b.sgp4_array(jd, fr)
    d = np.linalg.norm(ra - rb, axis=1)
    d[(ea != 0) | (eb != 0)] = np.inf
    k = int(np.argmin(d))
    return ts[k], float(d[k]), float(np.linalg.norm(va[k] - vb[k]))


def screen(star, others, t0, hours):
    A, sa, star, bad_a = build(star)
    B, sb, others, bad_b = build(others)
    n_steps = int(hours * 3600 / STEP_S)
    best = {}  # (i, j, encounter bucket) -> (estimated km, time)
    chunk = 120
    for c0 in range(0, n_steps, chunk):
        steps = range(c0, min(c0 + chunk, n_steps))
        ts = [t0 + timedelta(seconds=s * STEP_S) for s in steps]
        jd, fr = jdfr(ts)
        ea, ra, va = A.sgp4(jd, fr)
        eb, rb, vb = B.sgp4(jd, fr)
        for k, s in enumerate(steps):
            I, J = pairs_within(ra[:, k], rb[:, k], ea[:, k] == 0, eb[:, k] == 0)
            if not len(I):
                continue
            dr = ra[I, k] - rb[J, k]
            dv = va[I, k] - vb[J, k]
            vv = np.einsum("ij,ij->i", dv, dv)
            tau = -np.einsum("ij,ij->i", dr, dv) / np.maximum(vv, 1e-12)
            m = np.abs(tau) <= STEP_S / 2 + 1e-9  # minimum falls inside this step
            if not m.any():
                continue
            dmin = np.linalg.norm(dr[m] + dv[m] * tau[m, None], axis=1)
            for i, j, dm, tt in zip(I[m], J[m], dmin, tau[m]):
                if dm > REFINE_KM:
                    continue
                when = ts[k] + timedelta(seconds=float(tt))
                key = (int(i), int(j), int(s * STEP_S // 600))  # one encounter per 10 min
                if key not in best or dm < best[key][0]:
                    best[key] = (float(dm), when)
    events = []
    for (i, j, _), (est, when) in best.items():
        t, km, vrel = refine(sa[i], sb[j], when)
        if km <= REPORT_KM:
            events.append({"starlink": star[i], "other": others[j], "tca": t, "miss_km": km, "vrel_kms": vrel, "est_km": est})
    events.sort(key=lambda e: e["miss_km"])
    return events, {"starlink": len(star), "others": len(others), "unparsed": bad_a + bad_b, "steps": n_steps}, \
        [o["NORAD_CAT_ID"] for o in others]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--start")
    ap.add_argument("--out", default="screen.json")
    a = ap.parse_args()
    rows = load_rows(a.files)
    t0 = parse_epoch(a.start) if a.start else datetime.now(timezone.utc).replace(second=0, microsecond=0)
    star, others, dropped, band = select(rows, t0)
    import time
    t_start = time.time()
    events, stats, screened = screen(star, others, t0, a.hours)
    stats.update(dropped=dropped, band_km=[round(band[0]), round(band[1])], seconds=round(time.time() - t_start, 1),
                 start=t0.isoformat(), hours=a.hours, events=len(events))
    slim = [{
        "tca": e["tca"].isoformat(timespec="milliseconds"),
        "miss_km": round(e["miss_km"], 3), "vrel_kms": round(e["vrel_kms"], 2),
        "starlink": {"id": e["starlink"]["NORAD_CAT_ID"], "name": e["starlink"]["OBJECT_NAME"], "epoch": e["starlink"]["EPOCH"]},
        "other": {"id": e["other"]["NORAD_CAT_ID"], "name": e["other"]["OBJECT_NAME"], "intl": e["other"]["OBJECT_ID"],
                  "epoch": e["other"]["EPOCH"], "src": e["other"]["src"]},
    } for e in events]
    with open(a.out, "w") as f:
        json.dump({"stats": stats, "events": slim, "screened_others": screened}, f, indent=1)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
