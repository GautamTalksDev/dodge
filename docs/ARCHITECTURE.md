# Architecture

DODGE has four parts. None of them runs a server, holds a user account or stores personal data.

| Part | Where it runs | What it does |
|---|---|---|
| Recorder | GitHub Actions, every 4 hours | Downloads public orbit data from CelesTrak and keeps every new element set, because CelesTrak only serves the latest one |
| Screen | GitHub Actions, once a day | Predicts every pass under 5 km between Starlink and everything else for the next 24 hours, then attributes each pass |
| Data publication | GitHub Releases and the `data` branch | Daily archive (releases) and the latest files the site reads (`data` branch) |
| Website | Cloudflare Workers static assets | A static page that reads the latest files from the `data` branch |

## System overview

```mermaid
flowchart LR
  subgraph Sources["Public sources"]
    CT["CelesTrak GP data<br/>(active, analyst, debris, rocket bodies, last 30 days)"]
    SUP["CelesTrak SupGP<br/>(operator ephemerides: Starlink, OneWeb, Kuiper, Planet...)"]
    SAT["CelesTrak SATCAT<br/>(owner, type, launch)"]
  end

  subgraph GHA["GitHub Actions (least privilege)"]
    REC["record.yml<br/>every 4 h"]
    SCR["screen.yml<br/>daily 01:47 UTC"]
  end

  subgraph Store["GitHub storage"]
    REL[("Releases<br/>day-YYYY-MM-DD")]
    DB[("data branch<br/>latest.json, replay.json, starlink.json")]
    LOG["data/runs.ndjson<br/>run log"]
  end

  WEB["dodge.gautamkhosla.com<br/>Cloudflare static assets"]
  U["Reader's browser"]

  CT --> REC
  SUP --> REC
  SAT --> REC
  REC -->|"gp-*.ndjson.gz, satcat-*.csv.gz,<br/>supgp-sources-*.json"| REL
  REC --> LOG
  REL --> SCR
  SCR -->|"events-*.json.gz, summary-*.json"| REL
  SCR -->|"force-push, history replaced daily"| DB
  WEB -->|"HTML, CSS, JS, fonts"| U
  DB -->|"raw.githubusercontent.com (CORS *)"| U
```

## The daily screen, step by step

```mermaid
sequenceDiagram
  autonumber
  participant A as screen.yml
  participant R as Releases
  participant E as engine/daily.py
  participant S as engine/screen.py
  participant T as engine/attribute.py
  participant B as data branch

  A->>R: download yesterday's and today's recordings
  A->>A: run unit tests (fail closed)
  A->>E: start, t0 = now (UTC, whole minute)
  E->>S: select one element set per object
  Note over S: SupGP beats public sets.<br/>Closest epoch to t0 wins.<br/>Drop sets older than 7 days<br/>and objects that never reach<br/>the Starlink band.
  S->>S: SGP4 on a 10 s grid for 24 h
  S->>S: 100 km spatial hash per step
  S->>S: linear closest approach per candidate
  S->>S: refine under 10 km at 50 ms, keep under 5 km
  S-->>E: passes, screened object list
  E->>T: attribute by owner, fleet, type, launch, object
  T-->>E: summary
  E->>E: positions at closest approach, replay track, Starlink elements
  E-->>A: out/latest.json, replay.json, starlink.json, events, summary
  A->>R: upload events-*.json.gz and summary-*.json
  A->>B: replace the branch with the three latest files
```

## Repository layout

```
.github/workflows/   record.yml (recorder), screen.yml (screen, seal, sign), ci.yml, codeql.yml,
                     zizmor.yml, scorecard.yml, dependency-review.yml
recorder/record.py   downloads and deduplicates element sets; standard library only
engine/screen.py     selection, SGP4 propagation, spatial hash, closest approach, refinement
engine/attribute.py  joins passes with the SATCAT; owner, fleet, type, launch, object tables
engine/fleets.py     name patterns for fleets and which SupGP file would carry their ephemerides
engine/owners.json   SATCAT owner codes to display names
engine/daily.py      the daily run: screen, attribute, publish
tests/               unit tests (spatial hash, crafted crossing) and the recall check
tools/manifest.py    daily SHA-256 manifest, chained to the previous day
tools/verify.py      offline check of manifests and the chain
site/public/         the website: index.html, method/, app.js, globe.js, styles.css, _headers
site/build/          build helpers (land dots for the globe)
docs/                this documentation
data/runs.ndjson     one line per recorder run: sources, HTTP status, counts
```

## Why the data lives where it does

* **Releases** hold the archive. Each UTC day gets one release, `day-YYYY-MM-DD`, with the raw recordings and that day's results. Git history stays small and the archive is permanent.
* **The `data` branch** holds only the three files the website needs. It is replaced every day with a fresh single commit, so it never grows. The site reads it from `raw.githubusercontent.com`, which allows cross-origin reads.
* **`main`** holds code, docs and the small run log. Nothing large is committed to it.

## Design constraints

* **Public data only.** DODGE never uses Space-Track: its user agreement forbids passing on analysis without Department of Defense approval.
* **Gentle on CelesTrak.** At most one download per source per run, every 4 hours, well under the 250 MB per day limit. A 403 ("not updated since your last download") is skipped, never retried.
* **No server.** There is nothing to log in to and nothing to break into on the website. All computation happens in GitHub Actions, in the open.
* **Reproducible.** Every input is kept in the releases, the engine is deterministic for a given start time, and the dependencies are pinned. See [VERIFYING.md](VERIFYING.md).
