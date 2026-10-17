"""Build site/public/ledger/index.html from Maneuver Ledger's generated results page.

    python3 site/build/ledger_page.py ~/projects/maneuver-ledger

Maneuver Ledger (github.com/GautamTalksDev/maneuver-ledger) is a separate research
project that reads DODGE's sealed recordings. Its pipeline writes one static page,
site/index.html, in which every number is traced to its out/summary.json. This script
does not compute anything: it takes that page's <main> content unchanged and wraps it in
DODGE's header, footer and stylesheet, so the numbers are byte-for-byte the ones the
ledger's tests checked.

It refuses input that would weaken this site's Content Security Policy: no scripts,
no inline styles or style attributes, no external sources, links only to https:// or
to this site.
"""
import hashlib
import html
import os
import re
import subprocess
import sys

OUT = os.path.join(os.path.dirname(__file__), "..", "public", "ledger", "index.html")
REPO = "https://github.com/GautamTalksDev/maneuver-ledger"

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Maneuver Ledger: Starlink avoidance burns in public orbit data</title>
<meta name="description" content="How many of Starlink's collision-avoidance burns can public orbit data see? Public element sets against the manoeuvres SpaceX reported to the FCC, with the detection limit measured three ways.">
<meta property="og:title" content="Maneuver Ledger: Starlink avoidance burns in public orbit data">
<meta property="og:description" content="Public element sets cannot rebuild the avoidance manoeuvres SpaceX filed with the FCC. The detection limit is the result.">
<meta property="og:type" content="article">
<meta property="og:url" content="https://dodge.gautamkhosla.com/ledger/">
<meta property="og:image" content="https://dodge.gautamkhosla.com/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#08090c">
<link rel="canonical" href="https://dodge.gautamkhosla.com/ledger/">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/fonts/geist.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/styles.css">
<link rel="stylesheet" href="/ledger/ledger.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="bar">
  <a class="brand" href="/" aria-label="DODGE, home"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="16" cy="4" r="2.4" fill="#f4733b"/></svg>DODGE</a>
  <span></span>
  <nav class="nav" aria-label="Site"><a class="keep" href="/">Today</a><a class="keep" href="/method/">Method</a><a class="keep" href="/ledger/" aria-current="page">Ledger</a><a href="{repo}" rel="noopener">Code and data</a></nav>
</header>
<main class="prose ledger" id="main">
"""

ABOUT = """<h2>About this page</h2>
<p>Maneuver Ledger is a separate research project. It reads <a href="/">DODGE</a>'s sealed recordings of public orbit data and never records anything itself. Code, data, method and a byte-for-byte reproduction: <a href="{repo}" rel="noopener">github.com/GautamTalksDev/maneuver-ledger</a> (<a href="{repo}/blob/main/docs/METHODS.md" rel="noopener">method</a>, <a href="{repo}/blob/main/docs/FAQ.md" rel="noopener">questions</a>). Code Apache-2.0, derived data CC BY 4.0.</p>
<p class="cap">This page is generated from the ledger's results page at commit <code>{commit}</code> (SHA-256 of that page <code>{digest}</code>). Paths such as <code>out/summary.json</code> refer to that repository.</p>
"""

FOOT = """</main>
<footer class="foot">
  <div>
    <p>Orbit data from <a href="https://celestrak.org">CelesTrak</a> (Dr T.S. Kelso), recorded by DODGE. The reference count is SpaceX's own filing with the FCC. No Space-Track data.</p>
    <p>Independent project by <a href="https://gautamkhosla.com">Gautam Khosla</a>. Not affiliated with SpaceX or Starlink. Screening grade, not for operations.</p>
  </div>
  <div class="micro"><p><a href="/">Today</a> · <a href="/method/">Method</a> · <a href="/privacy/">Privacy</a> · <a href="{repo}/security/policy">Security</a> · <a href="{repo}/issues">Report an error</a></p></div>
</footer>
</body>
</html>
"""


def check(fragment):
    low = fragment.lower()
    if "<script" in low or "<style" in low or " style=" in low or re.search(r"\bsrc\s*=", low):
        raise SystemExit("refusing: the ledger page contains a script, a style or an external source")
    if re.search(r"\son[a-z]+\s*=", low):
        raise SystemExit("refusing: inline event handler")
    for href in re.findall(r'href="([^"]*)"', fragment):
        if not href.startswith(("https://", "/", "#")):
            raise SystemExit(f"refusing: link {href!r}")
    for bad in (chr(0x2013), chr(0x2014), "&mdash;", "&ndash;"):
        if bad in fragment:
            raise SystemExit("refusing: em or en dash")


def build(ledger_dir, out=OUT):
    src = os.path.join(ledger_dir, "site", "index.html")
    with open(src, "rb") as f:
        raw = f.read()
    page = raw.decode("utf-8")
    body = page.split("<main>", 1)[1].rsplit("</main>", 1)[0]
    check(body)
    try:
        commit = subprocess.run(["git", "-C", ledger_dir, "log", "-1", "--format=%h", "--", "site/index.html"],
                                capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    doc = (HEAD.format(repo=REPO) + body + ABOUT.format(repo=REPO, commit=html.escape(commit),
                                                       digest=hashlib.sha256(raw).hexdigest()[:16])
           + FOOT.format(repo=REPO))
    check(doc.split("<body>", 1)[1])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(build(os.path.expanduser(sys.argv[1])))
