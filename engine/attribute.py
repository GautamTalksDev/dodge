#!/usr/bin/env python3
"""DODGE attribution: who is on the other side of each Starlink close approach.

Joins screen.py events with the CelesTrak SATCAT (owner, type, launch) and
counts approaches by owner, object type, launch and object. Raw counts favour
whoever has the most hardware in the Starlink band, so every owner row also
carries how many of its objects were screened and the approaches per object.
"""
import csv
import gzip
import json
import os
import sys
from collections import Counter, defaultdict

from fleets import fleet_of

HERE = os.path.dirname(os.path.abspath(__file__))
TYPES = {"PAY": "Satellite", "R/B": "Rocket body", "DEB": "Debris", "UNK": "Unknown"}
TIERS = (5.0, 1.0, 0.5)


def load_json(path):
    """Read a JSON file and close it."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_satcat(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return {int(r["NORAD_CAT_ID"]): r for r in csv.DictReader(f)}


def launch_of(intl):
    return intl[:8] if intl and len(intl) >= 8 else None


def main(screen_path, satcat_path, out_path, sup_path=None):
    owners = load_json(os.path.join(HERE, "owners.json"))
    sc = load_satcat(satcat_path)
    data = load_json(screen_path)
    events, stats = data["events"], data["stats"]
    screened = data.get("screened_others", [])

    def owner(nid):
        r = sc.get(int(nid))
        return (r or {}).get("OWNER") or "UNK"

    exposure = Counter(owner(n) for n in screened)
    by_owner = defaultdict(lambda: Counter())
    by_type = defaultdict(lambda: Counter())
    by_launch = defaultdict(lambda: Counter())
    by_obj = defaultdict(lambda: Counter())
    meta_obj, meta_launch = {}, {}
    for e in events:
        o = e["other"]
        r = sc.get(int(o["id"]), {})
        own = r.get("OWNER") or "UNK"
        typ = r.get("OBJECT_TYPE") or "UNK"
        lid = launch_of(o.get("intl") or r.get("OBJECT_ID"))
        for t in TIERS:
            if e["miss_km"] <= t:
                k = f"under_{t:g}km"
                by_owner[own][k] += 1
                by_type[typ][k] += 1
                by_obj[o["id"]][k] += 1
                if lid:
                    by_launch[lid][k] += 1
        meta_obj[o["id"]] = {"name": o["name"], "intl": o.get("intl"), "owner": own, "type": TYPES.get(typ, typ),
                             "launched": r.get("LAUNCH_DATE")}
        if lid and lid not in meta_launch:
            meta_launch[lid] = {"owner": own, "launched": r.get("LAUNCH_DATE"), "site": r.get("LAUNCH_SITE")}

    total = Counter()
    for e in events:
        for t in TIERS:
            if e["miss_km"] <= t:
                total[f"under_{t:g}km"] += 1

    def rows(d, meta=None, limit=None, key="under_5km"):
        out = []
        for k, c in sorted(d.items(), key=lambda kv: -kv[1][key]):
            row = {"key": k, **{f"under_{t:g}km": c.get(f"under_{t:g}km", 0) for t in TIERS}}
            if meta is not None:
                row.update(meta.get(k, {}))
            out.append(row)
        return out[:limit] if limit else out

    owner_rows = rows(by_owner)
    for r in owner_rows:
        r["name"] = owners.get(r["key"], r["key"])
        r["objects_screened"] = exposure.get(r["key"], 0)
        r["per_object"] = round(r["under_5km"] / r["objects_screened"], 2) if r["objects_screened"] else None
        r["share"] = round(r["under_5km"] / max(total["under_5km"], 1), 4)
    type_rows = rows(by_type)
    for r in type_rows:
        r["name"] = TYPES.get(r["key"], r["key"])
    for r in rows(by_launch):
        pass
    # Fleets: payloads only, with exposure and public-ephemeris status.
    sup_files = set()
    if sup_path and os.path.exists(sup_path):
        sup_files = set(load_json(sup_path)["files"])
    fleet_exp, fleet_ev = Counter(), defaultdict(Counter)
    fleet_meta = {}
    for n in screened:
        r = sc.get(int(n), {})
        if r.get("OBJECT_TYPE") != "PAY":
            continue
        fl = fleet_of(r.get("OBJECT_NAME"))
        if fl:
            fleet_exp[fl[0]] += 1
            fleet_meta[fl[0]] = fl
    for e in events:
        r = sc.get(int(e["other"]["id"]), {})
        if r.get("OBJECT_TYPE") != "PAY":
            continue
        fl = fleet_of(r.get("OBJECT_NAME") or e["other"]["name"])
        if not fl:
            continue
        fleet_meta[fl[0]] = fl
        for t in TIERS:
            if e["miss_km"] <= t:
                fleet_ev[fl[0]][f"under_{t:g}km"] += 1
    fleet_rows = []
    for f, (name, op, sup) in fleet_meta.items():
        c = fleet_ev[f]
        n = fleet_exp.get(f, 0)
        fleet_rows.append({"fleet": name, "operator": op, "objects_screened": n,
                           **{f"under_{t:g}km": c.get(f"under_{t:g}km", 0) for t in TIERS},
                           "per_object": round(c.get("under_5km", 0) / n, 2) if n else None,
                           "public_ephemerides": bool(sup and sup in sup_files) if sup_files else None})
    fleet_rows.sort(key=lambda r: -r["under_5km"])

    # Hardware nobody can steer: rocket bodies and debris, by owner.
    dead = defaultdict(Counter)
    for e in events:
        r = sc.get(int(e["other"]["id"]), {})
        if r.get("OBJECT_TYPE") in ("R/B", "DEB"):
            own = r.get("OWNER") or "UNK"
            dead[own][r["OBJECT_TYPE"]] += 1
    dead_rows = sorted(({"key": k, "name": owners.get(k, k), "rocket_bodies": v["R/B"], "debris": v["DEB"],
                         "total": v["R/B"] + v["DEB"]} for k, v in dead.items()), key=lambda r: -r["total"])

    result = {
        "stats": stats,
        "by_fleet": fleet_rows,
        "dead_hardware": dead_rows,
        "totals": dict(total),
        "by_owner": owner_rows,
        "by_type": type_rows,
        "by_launch": rows(by_launch, meta_launch, 40),
        "by_object": rows(by_obj, meta_obj, 50),
    }
    with open(out_path, "w") as f:
        json.dump(result, f, indent=1)
    return result


if __name__ == "__main__":
    r = main(*sys.argv[1:5])
    print(json.dumps(r["totals"]))
    for row in r["by_fleet"][:20]:
        print(f'{row["fleet"][:30]:30} objs={row["objects_screened"]:5} <5km={row["under_5km"]:5} <1km={row["under_1km"]:4} per={row["per_object"]} public_eph={row["public_ephemerides"]}')
    for row in r["dead_hardware"][:6]:
        print("dead", row)
    for row in r["by_owner"][:12]:
        print(f'{row["key"]:5} {row["name"][:34]:34} {row["under_5km"]:6} {row["under_1km"]:5} share={row["share"]:.3f} objs={row["objects_screened"]} per={row["per_object"]}')
    for row in r["by_type"]:
        print(row["name"], row["under_5km"], row["under_1km"])
