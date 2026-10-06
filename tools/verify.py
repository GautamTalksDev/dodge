#!/usr/bin/env python3
"""Verify downloaded DODGE releases: file hashes and the day-to-day chain.

    gh release download day-2026-10-06 -D check
    gh release download day-2026-10-07 -D check
    python tools/verify.py check

For every manifest-*.json in the folder, oldest first:
  1. every file it lists that is present must match its SHA-256 and size;
  2. its "previous" link must equal the SHA-256 of the previous day's manifest,
     when that manifest is present.

It does not need the network. To also check that GitHub Actions in this
repository produced a manifest (Sigstore attestation):

    gh attestation verify check/manifest-2026-10-07.json --repo GautamTalksDev/dodge

Exit code 0 means everything present checked out.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifest import sha256_file  # noqa: E402


def main(folder):
    manifests = sorted(glob.glob(os.path.join(folder, "manifest-*.json")))
    if not manifests:
        print("no manifest-*.json files in", folder)
        return 1
    bad = 0
    by_day = {}
    for path in manifests:
        m = json.load(open(path))
        by_day[m["day"]] = path
        checked = 0
        for name, meta in m["files"].items():
            p = os.path.join(folder, name)
            if not os.path.exists(p):
                continue
            if os.path.getsize(p) != meta["bytes"] or sha256_file(p) != meta["sha256"]:
                print(f"MISMATCH {name} (manifest {m['day']})")
                bad += 1
            else:
                checked += 1
        link = "first link"
        if m["previous"]:
            prev_path = by_day.get(m["previous"]["day"])
            if prev_path is None:
                link = f"previous day {m['previous']['day']} not downloaded"
            elif sha256_file(prev_path) != m["previous"]["sha256"]:
                print(f"BROKEN CHAIN at {m['day']}: previous manifest {m['previous']['day']} changed")
                bad += 1
                link = "BROKEN"
            else:
                link = f"chained to {m['previous']['day']}"
        print(f"{m['day']}: {checked}/{len(m['files'])} files checked, {link}")
    print("OK" if not bad else f"{bad} problem(s)")
    return 0 if not bad else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
