# Data

Everything DODGE produces is public. This page lists every file, where it lives and what each field means.

## Where to get it

| What | Where | Updated |
|---|---|---|
| Latest summary (what the site shows) | [`data` branch: latest.json](https://raw.githubusercontent.com/GautamTalksDev/dodge/data/latest.json) | Daily |
| Replay track of every pass | [`data` branch: replay.json](https://raw.githubusercontent.com/GautamTalksDev/dodge/data/replay.json) | Daily |
| Starlink elements used by the globe | [`data` branch: starlink.json](https://raw.githubusercontent.com/GautamTalksDev/dodge/data/starlink.json) | Daily |
| Raw orbit recordings | [Releases](https://github.com/GautamTalksDev/dodge/releases), `day-YYYY-MM-DD`: `gp-YYYY-MM-DD.ndjson.gz` | Every 4 hours |
| Catalog snapshot | same release: `satcat-YYYY-MM-DD.csv.gz` | Daily |
| Operators that publish ephemerides | same release: `supgp-sources-YYYY-MM-DD.json` | Daily |
| Every pass under 5 km | same release: `events-YYYY-MM-DD.json.gz` | Daily |
| That day's summary | same release: `summary-YYYY-MM-DD.json` | Daily |
| Recorder run log | [`data/runs.ndjson`](../data/runs.ndjson) on `main` | Every 4 hours |

All times are UTC. Distances are kilometres and speeds kilometres per second unless a field name says otherwise.

## Raw recordings: `gp-YYYY-MM-DD.ndjson.gz`

One JSON object per line, one line per element set first seen that UTC day. Fields follow the CCSDS Orbit Mean-Elements Message (OMM) names that CelesTrak uses.

| Field | Meaning |
|---|---|
| `src` | Which download it came from: `starlink-supgp`, `supgp-<operator>`, `active`, `analyst`, `last-30-days`, `debris`, `rocket-bodies` |
| `NORAD_CAT_ID` | Catalog number (six digits since July 2026) |
| `OBJECT_ID` | International designator, for example `2026-062C` |
| `OBJECT_NAME` | Catalog name |
| `EPOCH` | Element set epoch, UTC |
| `MEAN_MOTION` | Revolutions per day (Kozai mean motion, as SGP4 expects) |
| `ECCENTRICITY`, `INCLINATION`, `RA_OF_ASC_NODE`, `ARG_OF_PERICENTER`, `MEAN_ANOMALY` | Mean orbital elements, degrees |
| `BSTAR`, `MEAN_MOTION_DOT`, `MEAN_MOTION_DDOT` | Drag and mean motion derivatives, as in a TLE |
| `EPHEMERIS_TYPE`, `CLASSIFICATION_TYPE`, `ELEMENT_SET_NO`, `REV_AT_EPOCH` | Housekeeping fields from the source |

`src` values starting with `supgp` are fits to the operator's own published ephemerides. They are far more accurate than the radar-based public sets and are preferred whenever both exist.

## Passes: `events-YYYY-MM-DD.json.gz`

A JSON array, closest first. One entry per predicted pass under 5 km.

| Field | Meaning |
|---|---|
| `tca` | Time of closest approach, UTC, millisecond precision |
| `miss_km` | Predicted miss distance at `tca` |
| `vrel_kms` | Relative speed at `tca` |
| `starlink.id`, `starlink.name`, `starlink.epoch` | The Starlink satellite and the epoch of the element set used |
| `other.id`, `other.name`, `other.intl`, `other.epoch`, `other.src` | The other object, its designator, epoch and source |

## Summary: `latest.json` and `summary-YYYY-MM-DD.json`

| Key | Contents |
|---|---|
| `day`, `generated_at` | Screen date and generation time |
| `stats` | `start` (t0), `hours` (24), `starlink` and `others` screened, `events`, `band_km` (altitude band screened), `dropped` (why objects were left out: `stale`, `outside_band`, `starlink_public_set`), `seconds` (run time), `inputs` |
| `totals` | `under_5km`, `under_1km`, `under_0.5km` |
| `by_owner` | Per SATCAT owner: passes per tier, `objects_screened`, `per_object` (passes under 5 km per object screened), `share` of all passes, display `name` |
| `by_fleet` | Per fleet (payloads only): `operator`, passes per tier, `objects_screened`, `per_object`, `public_ephemerides` (true when that day's SupGP list has the operator's file) |
| `by_type` | Satellite (`PAY`), rocket body (`R/B`), debris (`DEB`), unknown |
| `by_launch` | Top launches by passes, keyed by the launch part of the designator (`YYYY-NNN`) |
| `by_object` | Top objects by passes, with owner, type and launch date |
| `dead_hardware` | Per owner: passes involving rocket bodies and debris |
| `closest` | Every pass under 1 km, or the closest 300 if more. Each adds `at` (latitude, longitude, altitude in km at `tca`), `el` for both objects (see below), and the other object's `owner`, `owner_name`, `type`, `launched` |
| `public_ephemeris_files` | The SupGP operator files that existed that day |
| `brief` | `headline` and `lines`: plain sentences built by fixed templates from the numbers above (`engine/brief.py`), no language model |
| `maneuvers` | Once at least two days of history exist: `window_days`, `threshold_km`, and per fleet and owner the payloads screened and the share seen maneuvering (`engine/maneuvers.py`). `null` before that |

## Replay: `replay.json`

A JSON array, one entry per pass: `[unix_seconds, latitude, longitude, miss_metres, type, unregistered]`. `type` is 0 satellite, 1 rocket body, 2 debris, 3 unknown. `unregistered` is 1 when the SATCAT owner is `TBD`.

## Compact elements: `el` and `starlink.json`

`[inclination, raan, arg_of_perigee, mean_anomaly, mean_motion_rev_per_day, eccentricity, epoch_unix_seconds]`. The website uses these for drawing only (two-body motion with J2 drift). They are not precise enough to screen with.

## Licences and credit

* **Code:** MIT, see [LICENSE](../LICENSE).
* **DODGE's derived data** (passes, summaries, replay): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit "DODGE (dodge.gautamkhosla.com)".
* **Raw recordings** are CelesTrak data, republished unchanged with credit. CelesTrak's [usage policy](https://celestrak.org/NORAD/elements/) applies to them.
* **Catalog numbers, names and owners** come from the CelesTrak SATCAT.
