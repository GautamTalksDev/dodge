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
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import attribute  # noqa: E402
import screen  # noqa: E402

TOP_EVENTS = 300


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
    summary["closest"] = slim[:TOP_EVENTS]
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
