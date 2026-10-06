#!/usr/bin/env python3
"""Daily manifest: SHA-256 of every file DODGE published that day, chained to the day before.

    python tools/manifest.py DAY DIR [PREVIOUS_MANIFEST]

Writes DIR/manifest-DAY.json:

    {
      "day": "2026-10-07",
      "files": {"gp-2026-10-07.ndjson.gz": {"sha256": "...", "bytes": 123}, ...},
      "previous": {"day": "2026-10-06", "sha256": "<sha256 of that manifest file>"} | null,
      "generated_at": "..."
    }

Each manifest names the hash of the previous one, so the daily archive forms a
chain: changing any past file changes its manifest hash, which breaks every
later link. The manifest itself is then covered by a GitHub artifact
attestation (Sigstore), so anyone can check who produced it and from which
workflow run. tools/verify.py walks the chain.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

PUBLISHED = re.compile(r"^(gp|satcat|supgp-sources|events|summary)-\d{4}-\d{2}-\d{2}\.(ndjson\.gz|csv\.gz|json|json\.gz)$")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(day, folder, previous_path=None):
    files = {}
    for name in sorted(os.listdir(folder)):
        if PUBLISHED.match(name) and day in name:
            p = os.path.join(folder, name)
            files[name] = {"sha256": sha256_file(p), "bytes": os.path.getsize(p)}
    previous = None
    if previous_path and os.path.exists(previous_path):
        prev = json.load(open(previous_path))
        previous = {"day": prev["day"], "sha256": sha256_file(previous_path)}
    return {
        "day": day,
        "files": files,
        "previous": previous,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


if __name__ == "__main__":
    day, folder = sys.argv[1], sys.argv[2]
    prev = sys.argv[3] if len(sys.argv) > 3 else None
    m = build(day, folder, prev)
    out = os.path.join(folder, f"manifest-{day}.json")
    with open(out, "w") as f:
        json.dump(m, f, indent=1, sort_keys=True)
        f.write("\n")
    print(out, len(m["files"]), "files", "chained" if m["previous"] else "first link")
