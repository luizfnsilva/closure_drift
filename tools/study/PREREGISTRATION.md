# Pre-registration — closure_drift over the most-downloaded PyPI projects

Written 2026-10-04, before the list was built and before any repository in it was measured.

## The question

Among the 100 most-downloaded PyPI projects with a public source repository on GitHub, at how
many does a version label name more than one closure at a tag?

## The selection rule (fixed here; no repository is added or removed after seeing a result)

1. Source: `https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json` (30-day
   downloads), fetched once; its `last_update` is recorded.
2. Walk the ranking in order. For each project, read `https://pypi.org/pypi/<name>/json` and
   take the first URL, in the order `project_urls` values then `home_page`, that matches
   `github.com/<owner>/<repo>`. A project with none is recorded as `no_github_url` and skipped.
3. A repository already selected for an earlier project is recorded as `same_repository_as`
   and skipped: the unit is the repository.
4. Stop at 100 distinct repositories. The list, with rank and project name, is written to
   `tools/study/selection.tsv` and committed before the measurement starts.

## The measurement (fixed here)

- Each repository is cloned bare, with all tags, measured, and deleted.
- The detector is the one released as 0.8.0; its sha256 is recorded in the results and is the
  `detector_closure` of every report.
- **Defaults only**: `closure_drift.py <clone> --json`. No `--closure`, no `--version-file`, no
  `--tags`, no per-repository tuning of any kind. Where the defaults cannot find a version
  label, that is the result for that repository.
- A run that exceeds 15 minutes is recorded as `timeout`.
- Every repository appears in the results table, including refusals, timeouts and clones that
  failed. No row is dropped.

## What will be reported, whatever comes out

- Counts by outcome: `clean`, `drift`, `inconclusive`, `no_labels`, `empty_closure`,
  `no_publication_points`, refusal (by cause), `timeout`, `clone_failed`.
- Two fractions for drift, both: over the repositories where a determination was reached
  (`clean` + `drift`), and over all 100.
- For `clean` and `drift` rows, the coverage: points scanned, points compared.
- The limits, next to the numbers: the default closure globs are a guess about what determines
  each project's output; a monorepo that publishes several packages from one version file is in
  drift by its release scheme, not by an oversight; the 400 most recent tags are scanned.

## What will not be done

No repository's maintainers are contacted, no issue is opened anywhere, and no project is
described as badly run. Drift is a property of an addressing scheme.

## Run 2 — added 2026-10-04, after run 1 and before run 2

Run 1 is kept, with every row, in `run1/`. It is not replaced.

Run 1's result is mostly about the detector: 34 of 100 repositories refused for want of a version
label, and in 7 of 21 `drift` results the label read was a constant, not the released version.
The detector was changed for that (`tests/PREREGISTRATION.md` §9): the label source is resolved
at each tag, declared pointers are followed, and where the version is derived from the tag the
label is the tag.

Run 2 uses the **same selection** (`selection.tsv`, unchanged), the same rule of no
per-repository tuning, and the detector released as 0.9.0. Reported, whatever comes out:

- the same outcome counts as run 1, side by side with run 1's;
- for every `clean` and `drift` row, where the label came from (a file, or the tag), and how
  many of the points scanned were compared;
- `clean` results in which every label came from the tag, counted separately: there the label
  is the tag by construction, and "clean" says only that no two tags normalise to the same name;
- every repository whose outcome differs between the two runs, named.

A fall in the share of `drift` from run 1 to run 2 is as reportable as a rise.

## Run 3 — added 2026-10-05, before run 3

Runs 1 and 2 are kept as they are.

Run 3 measures the detector of release 0.10.0, which changes what `clean` requires and which
version files are believed (`tests/PREREGISTRATION.md` §10). The repositories have moved since
run 2, so run 3 is not compared with run 2 directly: **each clone is measured twice, with 0.10.0
and with 0.9.1**, and the difference between those two on the same clone is what is attributed to
the detector. Same selection, same rule of no tuning, the defaults only.

It runs on GitHub's runners (`.github/workflows/study.yml`, ten shards), not on the author's
machine; the platform is recorded with the results. Reported, whatever comes out: the outcome
counts of 0.10.0 and of 0.9.1 on the same clones; every repository whose outcome differs between
the two, named with the field that moved; the two denominators for drift, as before.

Expected from the stored reports of run 2: `coveragepy`, `scipy`, `tqdm` and `idna` move from
`clean` to `incomplete`. Anything else that moves is reported, not explained away.
