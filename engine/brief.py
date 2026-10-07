"""The daily brief: a few plain sentences built only from the day's numbers.

No language model: every sentence is a fixed template filled with computed
values, so the brief cannot state anything the data does not contain.
"""


def _fmt(n):
    return f"{n:,}"


def _dist(km):
    return f"{round(km * 1000)} m" if km < 1 else f"{km:.2f} km"


def build(s):
    t, st = s["totals"], s["stats"]
    lines = []
    head = (f"{_fmt(t['under_5km'])} predicted passes within 5 km of a Starlink satellite in the next 24 hours, "
            f"{_fmt(t['under_1km'])} of them within 1 km.")
    c = (s.get("closest") or [None])[0]
    if c:
        o = c["other"]
        lines.append(f"Closest: {c['starlink']['name']} and {o['name']} ({o.get('owner_name', o.get('owner'))}, "
                     f"{(o.get('type') or 'object').lower()}), predicted {_dist(c['miss_km'])} apart at "
                     f"{c['tca'][11:16]} UTC, closing at {c['vrel_kms']:.1f} km/s.")
    own = [r for r in s.get("by_owner", []) if r["key"] not in ("TBD", "UNK")][:2]
    if len(own) == 2:
        lines.append(f"Most passes: {own[0]['name']} ({_fmt(own[0]['under_5km'])}) and {own[1]['name']} "
                     f"({_fmt(own[1]['under_5km'])}); per object, {own[0]['per_object']:.2f} and {own[1]['per_object']:.2f}.")
    dead = s.get("dead_hardware", [])
    if dead:
        total = sum(r["total"] for r in dead)
        lines.append(f"{_fmt(total)} passes involve rocket bodies or debris; {dead[0]['name']} owns the most of that hardware.")
    tbd = next((r for r in s.get("by_owner", []) if r["key"] == "TBD"), None)
    if tbd:
        lines.append(f"Objects with no registered owner: {tbd['per_object']:.2f} passes each, across {_fmt(tbd['objects_screened'])} objects.")
    m = s.get("maneuvers")
    if m:
        fl = [f for f in m["by_fleet"] if f["payloads"] >= 5]
        if fl:
            still = min(fl, key=lambda f: f["share"])
            lines.append(f"Over {m['window_days']} days, {round(100 * still['share'])}% of {still['fleet']} satellites "
                         f"in Starlink's band were seen maneuvering.")
    lines.append(f"Screened {_fmt(st['starlink'])} Starlinks against {_fmt(st['others'])} objects from public data. "
                 "Screening grade, not collision probabilities.")
    return {"headline": head, "lines": lines}
