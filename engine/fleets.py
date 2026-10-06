"""Name patterns that group objects into fleets (constellations and families).

A fleet's public-ephemeris status comes from the CelesTrak SupGP file list of
that day (supgp-sources-YYYY-MM-DD.json), never from this table, so a fleet
that starts publishing shows up the next day without a code change.
"""
import re

# (fleet, operator, SupGP file that would carry its operator ephemerides, regex on OBJECT_NAME)
FLEETS = [
    ("Starlink", "SpaceX", "starlink", r"^STARLINK"),
    ("OneWeb", "Eutelsat OneWeb", "oneweb", r"^ONEWEB"),
    ("Kuiper", "Amazon", "kuiper", r"^KUIPER"),
    ("Qianfan (Thousand Sails)", "Shanghai Spacecom (SSST)", None, r"^QIANFAN"),
    ("Guowang", "China SatNet", None, r"^HULIANWANG"),
    ("Honghu", "Landspace / Shanghai Honghu", None, r"^HONGHU"),
    ("Jilin-1", "Chang Guang Satellite", None, r"^JILIN-1"),
    ("Yaogan", "PLA (military)", None, r"^YAOGAN"),
    ("Tianqi", "Guodian Gaoke", None, r"^TIANQI"),
    ("Geely GEESAT", "Geespace", None, r"^GEESAT"),
    ("Tianmu", "CMA / China", None, r"^TIANMU"),
    ("Planet (Flock, SkySat, Pelican)", "Planet", "planet", r"^(FLOCK|SKYSAT|PELICAN|TANAGER)"),
    ("Spire (Lemur)", "Spire", None, r"^LEMUR"),
    ("AST SpaceMobile", "AST SpaceMobile", "ast", r"^(SPACEMOBILE|BLUEBIRD|BLUEWALKER)"),
    ("Iridium", "Iridium", "iridium", r"^IRIDIUM"),
    ("Orbcomm", "Orbcomm", "orbcomm", r"^ORBCOMM"),
    ("Globalstar", "Globalstar", None, r"^GLOBALSTAR"),
    ("Lynk", "Lynk Global", None, r"^LYNK"),
    ("ICEYE", "ICEYE", None, r"^ICEYE"),
    ("Capella", "Capella Space", None, r"^CAPELLA"),
    ("Satellogic (NuSat)", "Satellogic", None, r"^NUSAT"),
    ("HawkEye 360", "HawkEye 360", None, r"^HAWK"),
    ("Swarm", "SpaceX (Swarm)", None, r"^SPACEBEE"),
    ("Tiangong space station", "China Manned Space", "css", r"^(CSS|TIANHE|WENTIAN|MENGTIAN|SHENZHOU|TIANZHOU)"),
    ("ISS", "NASA and partners", "iss", r"^(ISS|PROGRESS|SOYUZ|DRAGON|CYGNUS|CREW DRAGON)"),
    ("Cosmos (Russian military)", "Russia", None, r"^COSMOS \d+$"),
]
_COMPILED = [(f, op, sup, re.compile(rx)) for f, op, sup, rx in FLEETS]


def fleet_of(name):
    """(fleet, operator, supgp_file) for a payload name, or None."""
    n = (name or "").upper()
    for f, op, sup, rx in _COMPILED:
        if rx.search(n):
            return f, op, sup
    return None
