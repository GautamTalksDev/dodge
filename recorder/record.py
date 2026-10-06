#!/usr/bin/env python3
"""DODGE recorder: keeps the orbit history that CelesTrak does not.

CelesTrak serves only the latest element set per object, so DODGE records
its own history. Each run downloads every source once, keeps element sets it
has not seen before, and merges them into one gzipped NDJSON file per UTC day.

Rules we follow (celestrak.org/NORAD/documentation/gp-data-formats.php):
at most one download per update, never more often than every 2 hours, well
under 250 MB a day. A 403 means "not updated since your last download" and is
skipped, never retried.

Standard library only, so the CI runner needs nothing installed.
"""
import csv
import gzip
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

GP = "https://celestrak.org/NORAD/elements/gp.php?FORMAT=json&"
SOURCES = [
    # Operator-supplied Starlink ephemerides, fitted by CelesTrak (SupGP).
    ("starlink-supgp", "https://celestrak.org/NORAD/elements/supplemental/sup-gp.php?FILE=starlink&FORMAT=json"),
    ("active", GP + "GROUP=active"),
    ("analyst", GP + "GROUP=analyst"),
    ("last-30-days", GP + "GROUP=last-30-days"),
    ("debris", GP + "NAME=DEB"),
    ("rocket-bodies", GP + "NAME=R/B"),
]
# Other operators that publish their own ephemerides in LEO. Where these
# exist, screening uses them instead of the public radar-based sets.
SUP = "https://celestrak.org/NORAD/elements/supplemental/sup-gp.php?FORMAT=json&FILE="
for _f in ("planet", "oneweb", "kuiper", "ast", "iridium", "orbcomm", "iss", "css", "eumetsat", "telesat"):
    SOURCES.append(("supgp-" + _f, SUP + _f))
SATCAT = "https://celestrak.org/pub/satcat.csv"
UA = "DODGE recorder (+https://github.com/GautamTalksDev/dodge)"
KEEP = (
    "NORAD_CAT_ID", "OBJECT_ID", "OBJECT_NAME", "EPOCH", "MEAN_MOTION", "ECCENTRICITY",
    "INCLINATION", "RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY", "BSTAR",
    "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT", "EPHEMERIS_TYPE", "CLASSIFICATION_TYPE",
    "ELEMENT_SET_NO", "REV_AT_EPOCH",
)


def fetch(url):
    """Return (status, bytes). 403/404 come back as a status, not an exception."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, b""


def load_day(path):
    seen, rows = set(), []
    if os.path.exists(path):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                seen.add((r["src"], r["NORAD_CAT_ID"], r["EPOCH"]))
                rows.append(r)
    return seen, rows


def main(workdir):
    os.makedirs(workdir, exist_ok=True)
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    day_path = os.path.join(workdir, f"gp-{day}.ndjson.gz")
    seen, rows = load_day(day_path)
    run = {"ran_at": now.isoformat(timespec="seconds"), "sources": {}}

    for key, url in SOURCES:
        status, body = fetch(url)
        info = {"status": status, "bytes": len(body)}
        if status == 200:
            try:
                data = json.loads(body)
            except ValueError:
                # CelesTrak answers some errors with 200 and plain text.
                info["error"] = body[:120].decode("utf-8", "replace")
                data = []
            new = 0
            for o in data:
                rec = {k: o.get(k) for k in KEEP}
                rec["src"] = key
                k = (key, rec["NORAD_CAT_ID"], rec["EPOCH"])
                if k in seen:
                    continue
                seen.add(k)
                rows.append(rec)
                new += 1
            info.update(objects=len(data), new=new)
        run["sources"][key] = info
        time.sleep(2)  # be gentle between requests

    with gzip.open(day_path, "wt", encoding="utf-8", compresslevel=9) as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
    run["day_rows"] = len(rows)

    # The catalog (owner, type, launch) changes slowly: once a day is plenty.
    satcat_path = os.path.join(workdir, f"satcat-{day}.csv.gz")
    if not os.path.exists(satcat_path):
        status, body = fetch(SATCAT)
        if status == 200 and body.startswith(b"OBJECT_NAME,"):
            n = sum(1 for _ in csv.reader(io.StringIO(body.decode("utf-8")))) - 1
            with gzip.open(satcat_path, "wb", compresslevel=9) as f:
                f.write(body)
            run["satcat"] = {"status": status, "objects": n}
        else:
            run["satcat"] = {"status": status}

    # Which operators publish their own ephemerides through CelesTrak SupGP.
    # One small page a day; the list is what "publishes publicly" means on the site.
    sup_path = os.path.join(workdir, f"supgp-sources-{day}.json")
    if not os.path.exists(sup_path):
        status, body = fetch("https://celestrak.org/NORAD/elements/supplemental/")
        if status == 200:
            import re
            files = sorted(set(re.findall(rb"sup-gp\.php\?FILE=([A-Za-z0-9_-]+)", body)))
            with open(sup_path, "w") as f:
                json.dump({"checked_at": run["ran_at"], "files": [x.decode() for x in files]}, f)
            run["supgp_sources"] = len(files)

    print(json.dumps(run))
    return run


if __name__ == "__main__":
    out = main(sys.argv[1] if len(sys.argv) > 1 else "work")
    ok = any(s["status"] in (200, 403) for s in out["sources"].values())
    sys.exit(0 if ok else 1)
