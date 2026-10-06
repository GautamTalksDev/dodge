#!/usr/bin/env python3
"""Turn Natural Earth 110m land polygons into an even grid of dots for the globe.

Output: site/public/land.json, a flat [lat, lon, lat, lon, ...] list with one
decimal place. Dots are spaced STEP degrees in latitude and STEP/cos(lat) in
longitude, so they stay evenly spread on the sphere.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STEP = 1.6


def inside(lon, lat, ring):
    c = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def main():
    g = json.load(open(os.path.join(HERE, "land110.json")))
    polys = []
    for f in g["features"]:
        geom = f["geometry"]
        parts = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for p in parts:
            ring = p[0]
            xs = [x for x, _ in ring]
            ys = [y for _, y in ring]
            polys.append((min(xs), max(xs), min(ys), max(ys), ring, p[1:]))
    out = []
    lat = -88.0
    while lat <= 88.0:
        dlon = STEP / max(math.cos(math.radians(lat)), 0.05)
        lon = -180.0
        while lon < 180.0:
            for x0, x1, y0, y1, ring, holes in polys:
                if x0 <= lon <= x1 and y0 <= lat <= y1 and inside(lon, lat, ring) and not any(inside(lon, lat, h) for h in holes):
                    out += [round(lat, 1), round(lon, 1)]
                    break
            lon += dlon
        lat += STEP
    path = os.path.join(HERE, "..", "public", "land.json")
    with open(path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(len(out) // 2, "dots", os.path.getsize(path), "bytes")


if __name__ == "__main__":
    main()
