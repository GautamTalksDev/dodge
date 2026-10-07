"""Maneuver detection from the recorded element-set history.

Between two consecutive element sets of one object, the semi-major axis
should only shrink slowly under drag, at the rate the mean-motion derivative
predicts. A jump beyond that (THRESHOLD_KM) means the object fired a thruster.
Objects that never jump in the window cannot, or did not, move out of the way.

Needs at least two days of recordings; with less it returns None.
"""
import math
from collections import defaultdict
from datetime import datetime, timezone

MU = 398600.4418
THRESHOLD_KM = 0.25   # well above element-set noise for sma (tens of metres)
MAX_GAP_DAYS = 3.0    # longer gaps make drag extrapolation unreliable


def _epoch(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def sma_km(mean_motion_rev_day):
    n = float(mean_motion_rev_day) * 2 * math.pi / 86400.0
    return (MU / (n * n)) ** (1 / 3)


def detect(rows):
    """{norad_id: number of maneuvers seen}, plus the history span in days."""
    hist = defaultdict(list)
    for r in rows:
        if r.get("MEAN_MOTION") in (None, 0) or r["src"] == "starlink-supgp":
            continue
        hist[r["NORAD_CAT_ID"]].append(r)
    seen, first, last = {}, None, None
    for nid, rs in hist.items():
        rs.sort(key=lambda r: r["EPOCH"])
        count = 0
        for a, b in zip(rs, rs[1:]):
            ta, tb = _epoch(a["EPOCH"]), _epoch(b["EPOCH"])
            dt = (tb - ta).total_seconds() / 86400
            if dt <= 0 or dt > MAX_GAP_DAYS:
                continue
            first = ta if first is None or ta < first else first
            last = tb if last is None or tb > last else last
            n_pred = float(a["MEAN_MOTION"]) + 2 * float(a.get("MEAN_MOTION_DOT") or 0) * dt
            if n_pred <= 0:
                continue
            if abs(sma_km(b["MEAN_MOTION"]) - sma_km(n_pred)) > THRESHOLD_KM:
                count += 1
        seen[nid] = count
    span = (last - first).total_seconds() / 86400 if first and last else 0.0
    return seen, span


def summarise(rows, screened_ids, satcat, fleet_of, owners, min_days=2.0):
    seen, span = detect(rows)
    if span < min_days:
        return None
    by_fleet, by_owner = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for nid in screened_ids:
        r = satcat.get(int(nid), {})
        if r.get("OBJECT_TYPE") != "PAY" or nid not in seen:
            continue
        moved = seen[nid] > 0
        fl = fleet_of(r.get("OBJECT_NAME"))
        if fl:
            by_fleet[fl[0]][0] += 1
            by_fleet[fl[0]][1] += moved
        own = r.get("OWNER") or "UNK"
        by_owner[own][0] += 1
        by_owner[own][1] += moved
    pack = lambda d, label: sorted(({label: k, "payloads": v[0], "maneuvering": v[1],
                                     "share": round(v[1] / v[0], 3) if v[0] else None} for k, v in d.items()),
                                   key=lambda x: -x["payloads"])
    rows_owner = pack(by_owner, "key")
    for r in rows_owner:
        r["name"] = owners.get(r["key"], r["key"])
    return {"window_days": round(span, 1), "threshold_km": THRESHOLD_KM,
            "by_fleet": pack(by_fleet, "fleet"), "by_owner": rows_owner}
