#!/usr/bin/env python3
"""Write the SLSA provenance from a Sigstore bundle as in-toto JSON Lines.

    python tools/provenance.py attestation-DAY.sigstore.json provenance-DAY.intoto.jsonl

The bundle's DSSE envelope carries the signed in-toto statement with the
SLSA provenance predicate. *.intoto.jsonl is the conventional file for it,
one envelope per line.
"""
import json
import sys


def main(bundle_path, out_path):
    with open(bundle_path) as f:
        bundle = json.load(f)
    env = bundle.get("dsseEnvelope")
    if not isinstance(env, dict) or "payload" not in env or "signatures" not in env:
        raise SystemExit("bundle has no DSSE envelope")
    with open(out_path, "w") as f:
        f.write(json.dumps(env, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
