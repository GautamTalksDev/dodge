# DODGE

Who makes Starlink dodge.

Starlink reported 355,000+ collision-avoidance maneuvers in one year. Screening for close approaches is now free (SpaceX Stargaze, TraCSS, Space-Track). What nobody publishes is the other half: which objects and operators cause that risk, who shares their orbit data, and who leaves hardware behind.

DODGE is building that record in the open, from public data only.

## Status

Recording. CelesTrak serves only the latest orbit for each object, so DODGE keeps its own history, starting 6 Oct 2026. Every 4 hours `.github/workflows/record.yml` saves each new element set into that UTC day's release (`day-YYYY-MM-DD`). `data/runs.ndjson` logs every run.

## Sources

- [CelesTrak](https://celestrak.org) GP data: active satellites, analyst objects, last 30 days of launches, all debris, all rocket bodies.
- CelesTrak [SupGP](https://celestrak.org/NORAD/elements/supplemental/) for Starlink: orbits from SpaceX's own ephemerides, far more accurate than public element sets.
- CelesTrak SATCAT for owner, type and launch.

DODGE does not use Space-Track data.

## What the numbers will and will not mean

Public element sets are accurate to around a kilometre at best. DODGE results are screening grade: they show who comes close and how often. They are not collision probabilities, and they are not what Starlink's own system sees.

## Licence

Code: MIT. Data: CelesTrak, credited.
