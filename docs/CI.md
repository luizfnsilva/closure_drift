# Running closure_drift in a pipeline

The tool is non-interactive: it reads no standard input, asks no question, and its exit code is
the answer — `0` pass, `1` drift, `2` nothing could be determined (cause named). Two things every
recipe below needs: **the tags** (a shallow checkout has none) and **Python 3.9+ with git**.

## GitHub Actions

Before a release — would this commit's version reuse a label that already names other code?

```yaml
jobs:
  version-label:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: luizfnsilva/closure_drift@v1.1.0        # mode: would-tag (default)
```

The whole tag history, on a schedule, with a family of tags and a strict verdict:

```yaml
      - uses: luizfnsilva/closure_drift@v1.1.0
        with:
          mode: measure
          args: --tags 'v*' --strict
```

The action writes annotations and a job summary from the JSON report, and exposes `verdict` and
`exit-code` as outputs. `allow-undetermined: true` lets exit `2` pass; the default is to fail,
because an absence of measurement is not a pass.

Without the action (the package is installed from the release; it is not on PyPI):

```yaml
      - run: pipx run --spec https://github.com/luizfnsilva/closure_drift/releases/download/v1.1.0/closure_drift-1.1.0-py3-none-any.whl closure-drift --would-tag
```

## GitLab CI

```yaml
version-label:
  image: python:3.13
  variables:
    GIT_DEPTH: "0"              # full history, so the tags are there
  script:
    - git fetch --tags --force
    - pip install https://github.com/luizfnsilva/closure_drift/releases/download/v1.1.0/closure_drift-1.1.0-py3-none-any.whl
    - closure-drift --would-tag
```

## A release script, a Makefile, a pre-push hook

```bash
# release.sh — stop before the tag, not after
closure-drift --would-tag || { echo "the version was not bumped"; exit 1; }
git tag "v$(cat VERSION)" && git push --tags
```

```make
check-version-label:
	closure-drift --would-tag
```

```yaml
# .pre-commit-config.yaml — runs on git push
- repo: https://github.com/luizfnsilva/closure_drift
  rev: v1.1.0
  hooks:
    - id: closure-drift-would-tag
```

## Consuming the result

`--json` prints one object; its fields, the meaning of each verdict and the compatibility rules are
a contract, in [`REPORT.md`](REPORT.md). Read `verdict`, not the text.

```bash
closure-drift --json > report.json; code=$?
python3 -c "import json; r=json.load(open('report.json')); print(r['verdict'], r.get('points_without_label'))"
exit $code
```

When something looks wrong, run it again with `--diagnose` and paste the first lines into the
issue: versions, options and facts about the repository, with no label and no path of yours.
