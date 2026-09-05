## What this changes, and why

<!-- One paragraph. If it is a fix, say what was wrong. -->

## Checks

- [ ] `python3 tests/fixture_label_only.py` prints `fixture ok`
- [ ] `python3 tools/verify_deposit.py` still verifies
- [ ] No new dependency, no network access, nothing written to the measured repository

## If this touches the measurement script

- [ ] I have said what this does to **results already published** — the CHANGELOG entry is the point

<!--
The nine files listed in DEPOSIT.sha256 are byte-identical to the Zenodo deposit and are gated by
CI. A change to one of them is not refused, but it ships with the next deposit rather than in this
pull request. See CONTRIBUTING.md.
-->
