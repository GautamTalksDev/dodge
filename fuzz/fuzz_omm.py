#!/usr/bin/python3
"""Fuzz the path every third-party orbit record takes: OMM fields into SGP4.

CelesTrak data is untrusted input. The screen turns each record into an SGP4
satellite with sgp4.omm.initialize (C extension underneath) and propagates
it. A malformed record must be rejected with an ordinary Python exception or
an SGP4 error code, never crash the interpreter, hang, or loop forever.
"""
import sys

import atheris

with atheris.instrument_imports():
    from sgp4 import omm
    from sgp4.api import Satrec

FIELDS = ("MEAN_MOTION", "ECCENTRICITY", "INCLINATION", "RA_OF_ASC_NODE", "ARG_OF_PERICENTER",
          "MEAN_ANOMALY", "BSTAR", "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT")
EXPECTED = (ValueError, KeyError, TypeError, OverflowError, ZeroDivisionError, IndexError)


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    fields = {
        "OBJECT_NAME": fdp.ConsumeUnicodeNoSurrogates(24),
        "OBJECT_ID": fdp.ConsumeUnicodeNoSurrogates(12),
        "NORAD_CAT_ID": str(fdp.ConsumeIntInRange(0, 999999)),
        "EPOCH": fdp.PickValueInList(["2026-10-07T01:47:00.000000", "1957-10-04T00:00:00", "2100-01-01T00:00:00"])
        if fdp.ConsumeBool() else fdp.ConsumeUnicodeNoSurrogates(32),
        "CLASSIFICATION_TYPE": fdp.ConsumeUnicodeNoSurrogates(2),
        "ELEMENT_SET_NO": str(fdp.ConsumeIntInRange(0, 9999)),
        "REV_AT_EPOCH": str(fdp.ConsumeIntInRange(0, 99999)),
        "EPHEMERIS_TYPE": str(fdp.ConsumeIntInRange(0, 9)),
    }
    for k in FIELDS:
        if fdp.ConsumeBool():
            fields[k] = repr(fdp.ConsumeRegularFloat())
        else:
            fields[k] = fdp.ConsumeUnicodeNoSurrogates(16)
    sat = Satrec()
    try:
        omm.initialize(sat, fields)
    except EXPECTED:
        return
    for minutes in (0.0, 90.0, 1440.0, fdp.ConsumeRegularFloat()):
        try:
            sat.sgp4_tsince(minutes)
        except EXPECTED:
            return


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
