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
