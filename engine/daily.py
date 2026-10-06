#!/usr/bin/env python3
"""Daily DODGE run: screen the next 24 hours and publish the summary.

    python engine/daily.py WORKDIR OUTDIR

WORKDIR holds the recorder's files (gp-*.ndjson.gz, satcat-*.csv.gz,
supgp-sources-*.json). OUTDIR gets:
  latest.json          what the site reads
  days/YYYY-MM-DD.json the same summary, kept per day
  events-YYYY-MM-DD.json.gz  every approach under 5 km (for the release)
"""
import glob
import gzip
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import attribute  # noqa: E402
import screen  # noqa: E402

TOP_EVENTS = 300


def gmst(t):
    """Greenwich mean sidereal angle in radians (IAU 1982), good to visualise."""
    jd, fr = screen.jdfr([t])
    d = (jd[0] - 2451545.0) + fr[0]
    tt = d / 36525.0
    g = 280.46061837 + 360.98564736629 * d + 0.000387933 * tt * tt - tt ** 3 / 38710000.0
    return math.radians(g % 360.0)


def where(o, t):
    """Geocentric lat, lon (deg) and altitude (km) of object o at time t."""
    s = screen.satrec(o)
    jd, fr = screen.jdfr([t])
    e, r, _ = s.sgp4(jd[0], fr[0])
    if e:
        return None
    x, y, z = r
    rr = math.sqrt(x * x + y * y + z * z)
    lon = math.degrees(math.atan2(y, x) - gmst(t))
    lon = (lon + 180.0) % 360.0 - 180.0
    return round(math.degrees(math.asin(z / rr)), 2), round(lon, 2), round(rr - 6378.137, 1)


def compact_elements(objs):
    """[inc, raan, argp, mean anomaly, mean motion, ecc, epoch unix s] per object, for the browser globe."""
    out = []
    for o in objs:
        ep = screen.parse_epoch(o["EPOCH"]).timestamp()
        out.append([round(float(o[k]), 4) for k in ("INCLINATION", "RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY")]
                   + [round(float(o["MEAN_MOTION"]), 6), round(float(o["ECCENTRICITY"]), 6), int(ep)])
    return out


def newest(pattern):
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


def main(work, out):
    os.makedirs(os.path.join(out, "days"), exist_ok=True)
    gp = sorted(glob.glob(os.path.join(work, "gp-*.ndjson.gz")))[-2:]  # today and yesterday
    satcat = newest(os.path.join(work, "satcat-*.csv.gz"))
    sup = newest(os.path.join(work, "supgp-sources-*.json"))
    rows = screen.load_rows(gp)
    t0 = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    star, others, dropped, band = screen.select(rows, t0)
    started = time.time()
    events, stats, screened = screen.screen(star, others, t0, 24)
    stats.update(dropped=dropped, band_km=[round(band[0]), round(band[1])], seconds=round(time.time() - started, 1),
                 start=t0.isoformat(), hours=24, events=len(events), inputs=[os.path.basename(p) for p in gp])
    slim = [{
        "tca": e["tca"].isoformat(timespec="milliseconds"),
        "miss_km": round(e["miss_km"], 3), "vrel_kms": round(e["vrel_kms"], 2),
        "starlink": {"id": e["starlink"]["NORAD_CAT_ID"], "name": e["starlink"]["OBJECT_NAME"], "epoch": e["starlink"]["EPOCH"]},
        "other": {"id": e["other"]["NORAD_CAT_ID"], "name": e["other"]["OBJECT_NAME"], "intl": e["other"]["OBJECT_ID"],
                  "epoch": e["other"]["EPOCH"], "src": e["other"]["src"]},
    } for e in events]
    day = t0.strftime("%Y-%m-%d")
    raw = os.path.join(out, f"screen-{day}.json")
    with open(raw, "w") as f:
        json.dump({"stats": stats, "events": slim, "screened_others": screened}, f)
    summary = attribute.main(raw, satcat, os.path.join(out, f"attr-{day}.json"), sup)
    sc = attribute.load_satcat(satcat)
    owners = json.load(open(os.path.join(HERE, "owners.json"), encoding="utf-8"))
    # Keep every pass under 1 km (for the live countdown) and at least TOP_EVENTS.
    keep = max(TOP_EVENTS, sum(1 for e in events if e["miss_km"] < 1.0))
    closest = [json.loads(json.dumps(s)) for s in slim[:keep]]  # copies: slim stays whole for the release file
    for e, s in zip(events[:keep], closest):
        s["at"] = where(e["starlink"], e["tca"])
        # Elements of both objects, so the page can draw the two orbits crossing.
        s["starlink"]["el"] = compact_elements([e["starlink"]])[0]
        s["other"]["el"] = compact_elements([e["other"]])[0]
        r = sc.get(int(s["other"]["id"]), {})
        own = r.get("OWNER") or "UNK"
        s["other"].update(owner=own, owner_name=owners.get(own, own),
                          type=attribute.TYPES.get(r.get("OBJECT_TYPE"), "Unknown"), launched=r.get("LAUNCH_DATE"))
    summary["closest"] = closest
    # Every approach, coarsely, for the globe's 24 h replay: [unix s, lat, lon, miss m].
    replay = []
    for e in events:
        p = where(e["starlink"], e["tca"])
        if p:
            replay.append([int(e["tca"].timestamp()), round(p[0], 1), round(p[1], 1), int(e["miss_km"] * 1000)])
    with open(os.path.join(out, "replay.json"), "w") as f:
        json.dump(replay, f, separators=(",", ":"))
    with open(os.path.join(out, "starlink.json"), "w") as f:
        json.dump({"generated_at": t0.isoformat(), "elements": compact_elements(star)}, f, separators=(",", ":"))
    summary["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary["day"] = day
    if sup:
        summary["public_ephemeris_files"] = json.load(open(sup))["files"]
    for path in (os.path.join(out, "latest.json"), os.path.join(out, "days", f"{day}.json")):
        with open(path, "w") as f:
            json.dump(summary, f, separators=(",", ":"))
    with gzip.open(os.path.join(out, f"events-{day}.json.gz"), "wt") as f:
        json.dump(slim, f, separators=(",", ":"))
    os.remove(raw)
    os.remove(os.path.join(out, f"attr-{day}.json"))
    print(json.dumps({"day": day, **summary["totals"], "seconds": stats["seconds"]}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
