# Changelog

Every change that can move a published number is listed here, with the date it took effect. Dates are UTC.

## 2026-10-07: first public release

### Added

* Recorder (`recorder/record.py`, `record.yml`): every 4 hours, CelesTrak GP groups (active, analyst, last 30 days, all debris, all rocket bodies), SupGP for Starlink and ten other operators, and the SATCAT. New element sets go into that day's release.
* Screen (`engine/screen.py`): SGP4 on a 10 s grid for 24 hours, a 100 km spatial hash, a straight-line closest approach per candidate, and 50 ms SGP4 refinement. Passes under 5 km are reported.
* Attribution (`engine/attribute.py`, `engine/fleets.py`): owner, fleet, type, launch and object tables, per-object rates, hardware nobody can steer, and public ephemeris status.
* Daily publication (`engine/daily.py`, `screen.yml`): the `data` branch for the website, plus the events and summary in each day's release.
* Website at dodge.gautamkhosla.com: live globe, 24 hour replay, focus view of single passes, leaderboards, a countdown to the next pass under 1 km.
* Validation: spatial hash exactness test, crafted crossing test, recall check against brute force (80 of 80 on 6 October 2026).

### Method decisions

* Operator ephemerides (SupGP) are preferred over public sets for the same object.
* The element set closest to the screen start is used, not simply the newest.
* Starlink to Starlink passes are out of scope.
