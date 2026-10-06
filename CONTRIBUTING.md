# Contributing to DODGE

Thank you for helping. DODGE is a public record, so accuracy matters more than speed. Every change has to keep the numbers checkable.

## Ways to help

* **Report a wrong number.** Open an issue with the "Data correction" form. Include the object (NORAD number), the date of the screen, what DODGE says and what you believe is right, with a source.
* **Improve a fleet mapping.** Fleet names are regex patterns in [`engine/fleets.py`](engine/fleets.py). A pull request that adds or fixes a fleet should cite where the naming comes from.
* **Improve the method.** Open a discussion first. Changes to screening or attribution need a validation run: see [docs/VALIDATION.md](docs/VALIDATION.md).
* **Fix the website.** Plain HTML, CSS and JavaScript in `site/public/`. No frameworks and no third-party scripts. The Content Security Policy in `site/public/_headers` must stay strict.

## Security issues

Do not open a public issue. Follow [SECURITY.md](SECURITY.md).

## Set up

```bash
git clone https://github.com/GautamTalksDev/dodge.git
cd dodge
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.txt
.venv/bin/python -m unittest discover -s tests -p "test_*.py"
```

To run a screen locally, download a day's recordings from the [releases](https://github.com/GautamTalksDev/dodge/releases) into `work/`:

```bash
gh release download day-2026-10-06 -D work -p "gp-*" -p "satcat-*" -p "supgp-sources-*"
.venv/bin/python engine/daily.py work out
```

To preview the site, serve `site/public/` with any static server, and put a copy of `out/*.json` in `site/public/public-data/`. That folder is ignored by git and by deploys.

## Pull requests

* One change per pull request, with a clear description of why.
* Tests pass: `python -m unittest discover -s tests -p "test_*.py"`.
* If the change can move any published number, include a before and after for one real day.
* New dependencies need a strong reason. Pin them with hashes in `requirements.txt`.
* GitHub Actions must be pinned to a full commit SHA, with the version in a comment.
* Write for the reader: plain words, no em or en dashes in user-facing text.
* Commits do not need a sign-off, but they must be yours to contribute under the MIT licence.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be kind, be precise, assume good faith.
