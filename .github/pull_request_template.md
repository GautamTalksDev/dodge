## What and why

## Checklist

- [ ] Tests pass: `python -m unittest discover -s tests -p "test_*.py"`
- [ ] If this can move a published number: before and after for one real day, and a CHANGELOG entry
- [ ] New actions pinned to a full commit SHA; new Python dependencies pinned with hashes
- [ ] No `${{ }}` expressions inside `run:` blocks; no new write permissions in jobs that run third-party code
- [ ] User-facing text has no em or en dashes
