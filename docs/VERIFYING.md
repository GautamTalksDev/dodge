# Verifying DODGE data

You do not have to trust DODGE. Every published file can be checked three ways: that it has not changed, that this repository's workflow produced it, and that the archive has not been rewritten.

You need the [GitHub CLI](https://cli.github.com) and Python 3.

## 1. Download a day and the day before it

```bash
gh release download day-2026-10-08 -R GautamTalksDev/dodge -D check
gh release download day-2026-10-07 -R GautamTalksDev/dodge -D check
```

## 2. Check the hashes and the chain

```bash
python tools/verify.py check
```

```
2026-10-07: 5/5 files checked, first link
2026-10-08: 5/5 files checked, chained to 2026-10-07
OK
```

`verify.py` uses no network and no dependencies. For each day it confirms that every file matches its manifest, and that the manifest names the exact SHA-256 of the previous day's manifest. If anyone changed an earlier file, the chain breaks from that day on.

## 3. Check who produced it

Each day's release has an attestation, signed through Sigstore by this repository's `screen` workflow and recorded in the public Rekor transparency log.

```bash
gh attestation verify check/manifest-2026-10-07.json -R GautamTalksDev/dodge \
  --signer-workflow GautamTalksDev/dodge/.github/workflows/screen.yml
gh attestation verify check/events-2026-10-08.json.gz -R GautamTalksDev/dodge
```

A manifest for day N is attested in the release for day N+1, when the day is sealed.

## 4. Check the files the website reads

The `data` branch carries `SHA256SUMS-YYYY-MM-DD` next to the three files the site uses:

```bash
git clone --branch data --depth 1 https://github.com/GautamTalksDev/dodge.git dodge-data
cd dodge-data && sha256sum -c --ignore-missing SHA256SUMS-*
gh attestation verify latest.json -R GautamTalksDev/dodge
```

## 5. Reproduce a screen

The recordings in each release are everything the screen used, so you can rerun it:

```bash
git clone https://github.com/GautamTalksDev/dodge.git && cd dodge
python3 -m venv .venv && .venv/bin/pip install --require-hashes --no-deps -r requirements.txt
gh release download day-2026-10-07 -D work -p "gp-*" -p "satcat-*" -p "supgp-sources-*"
.venv/bin/python engine/screen.py work/gp-2026-10-07.ndjson.gz --start 2026-10-07T01:47:00 --out mine.json
```

Use the `start` time from that day's summary (`stats.start`). Results match to the metre on the same platform. Across processors, the last digit of a floating point sum can differ, which can move a borderline pass across the 5 km line. Totals agree to within a handful of passes.
