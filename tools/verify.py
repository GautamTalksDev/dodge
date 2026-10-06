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


def load_manifest(path):
    """Parse a manifest, or return None if it is not a well-formed DODGE manifest.

    A manifest is attacker-controllable input to this tool (anyone can hand
    you a folder), so its shape is checked before anything trusts it.
    """
    try:
        with open(path, "rb") as f:
            m = json.loads(f.read().decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(m, dict) or not isinstance(m.get("day"), str) or not isinstance(m.get("files"), dict):
        return None
    for name, meta in m["files"].items():
        if (not isinstance(name, str) or os.path.basename(name) != name or name in ("", ".", "..")
                or not isinstance(meta, dict) or not isinstance(meta.get("sha256"), str)
                or not isinstance(meta.get("bytes"), int)):
            return None
    prev = m.get("previous")
    if prev is not None and not (isinstance(prev, dict) and isinstance(prev.get("day"), str) and isinstance(prev.get("sha256"), str)):
        return None
    return m


def main(folder):
    manifests = sorted(glob.glob(os.path.join(folder, "manifest-*.json")))
    if not manifests:
        print("no manifest-*.json files in", folder)
        return 1
    bad = 0
    by_day = {}
    for path in manifests:
        m = load_manifest(path)
        if m is None:
            print(f"MALFORMED {os.path.basename(path)}")
            bad += 1
            continue
        by_day[m["day"]] = path
        checked = 0
        for name, meta in m["files"].items():
            # Names are plain file names (checked above), so this stays inside the folder.
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
