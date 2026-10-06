#!/usr/bin/python3
"""Fuzz tools/verify.py with hostile manifests.

Anyone can hand a reader a folder of "DODGE data". The verifier must report
malformed or malicious manifests, never crash, and never read a file outside
the folder it was given.
"""
import os
import sys
import tempfile

import atheris

with atheris.instrument_imports():
    import manifest  # tools/, put on the path at build time
    import verify

SENTINEL = os.path.join(tempfile.gettempdir(), "dodge-fuzz-outside")


def TestOneInput(data):
    with open(SENTINEL, "w") as f:
        f.write("outside")
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "manifest-2026-10-07.json"), "wb") as f:
            f.write(data)
        with open(os.path.join(d, "gp-2026-10-07.ndjson.gz"), "wb") as f:
            f.write(b"x")
        # Track every file the verifier opens; nothing outside d is allowed.
        real_open = open
        opened = []

        def guarded(path, *a, **k):
            opened.append(os.path.realpath(path))
            return real_open(path, *a, **k)

        verify.open = manifest.open = guarded  # module-level name lookups go here first
        try:
            rc = verify.main(d)
        finally:
            del verify.open, manifest.open
        assert rc in (0, 1, 2), rc
        root = os.path.realpath(d)
        for p in opened:
            assert p.startswith(root + os.sep), f"opened outside the folder: {p}"


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
