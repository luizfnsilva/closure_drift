# closure_drift

**Does `v1.4.2` mean one thing in your repository?**

```
$ closure-drift lodash
DRIFT: 69 of 78 labels name more than one closure
at a publication point. The worst covers 4.
```

A version is a string a human edits. When two releases share a version and differ in code, one
address names two artefacts — and nothing notices, because the version is all that was recorded.

One command checks it. Read-only, one file, no dependencies, no network.

## Run it

```bash
curl -sO https://raw.githubusercontent.com/luizfnsilva/closure_drift/v0.9.0/closure_drift.py
python3 closure_drift.py            # inside any git repository
```

or `pipx run --spec git+https://github.com/luizfnsilva/closure_drift@v0.9.0 closure-drift`.
Needs Python 3.9+ and git. To see the three possible answers first: `python3 examples/demo.py`.

## Check before you tag

`--would-tag` answers: *if I tag this commit now, does its version already name different code?*

```yaml
# GitHub Actions
- uses: actions/checkout@v4
  with: { fetch-depth: 0 }
- uses: luizfnsilva/closure_drift@v0.9.0
```

```yaml
# pre-commit, on git push
- repo: https://github.com/luizfnsilva/closure_drift
  rev: v0.9.0
  hooks: [{ id: closure-drift-would-tag }]
```

Other pipelines: [`docs/CI.md`](docs/CI.md).

## The answer

| verdict | exit | |
|---|---|---|
| `clean` | 0 | every label names one closure, over the points compared |
| `drift` | 1 | a label names more than one closure |
| `inconclusive`, `incomplete`, `no_labels`, `empty_closure`, `no_publication_points` | 2 | not enough to tell; the report says why |
| refusal | 2 | cause on stderr |

Exit 0 means `clean` and nothing else. No input produces a traceback; no failure exits 1.

- **label** — the version in your version file at each tag
- **closure** — SHA-256 over `(path, git object id)` of the files that determine your output

The report also says how many tags it could **not** compare.

## Options

| | |
|---|---|
| `--would-tag` | would tagging this commit reuse a label? |
| `--tags 'py-*'` | only these tags are publication points (monorepos) |
| `--at commits` | you publish at every commit |
| `--closure 'src/**'` | which files determine your output |
| `--strict` | `clean` only if every point was compared |
| `--explain LABEL` | which paths differ under a label in drift |
| `--compare A B` | two tags side by side |
| `--version-file`, `--version-regex` | where the label is |
| `--json`, `--badge`, `--diagnose` | report ([contract](docs/REPORT.md)), README badge, bug-report block |

Settings can be committed in `.closure-drift.json`. Flags override it; a broken file is refused.

## What it found

**The 100 most-downloaded PyPI projects, at the defaults** — rule and method fixed before the first
run ([`tools/study/`](tools/study/STUDY.md)):

@@STUDY@@

Earlier measurements, on repositories chosen by the author:

| Repository | Tags | Labels | In drift | Verdict |
|---|---|---|---|---|
| `pallets/click` | 68 | 10 | 0 | clean |
| `psf/requests` | 66 | 12 | 0 | clean |
| `pypa/packaging` | 17 | 13 | 0 | clean |
| `encode/httpx` | 28 | 28 | 0 | clean |
| `impress/impress.js` | 15 | 4 | 2 | **drift** |
| `lodash/lodash` | 400 of 440 | 78 | 69 | **drift** |
| `pola-rs/polars` | 400 of 570 | 51 | 40 | **drift** |

Two causes: a release tagged without bumping the version (`impress.js`), and tag families sharing
one version file (`lodash`, `polars`). Neither project is badly run. `--would-tag` addresses the
first, `--tags` the second.

## Limits

- It never runs your code and attests nothing. `clean` is about addressing, not reproducibility.
- A change of file mode alone is not seen.
- `tests/`, `docs/`, `vendor/`, `node_modules/` and `*.md` are never in the closure.
- The default closure globs are a guess. Pass `--closure`.

More: [`SCOPE.md`](SCOPE.md), [`docs/WHY.md`](docs/WHY.md).

## Safety

It starts `git` and nothing else, never writes to the repository, and does not run commands named
in that repository's git config. Details and reporting: [`SECURITY.md`](SECURITY.md).

## Tests

Three batteries, each pre-registered before the code. Scores are never added together.

| battery | macOS, Python 3.9 and 3.14 |
|---|---|
| `tests/battery.py` — acceptance proofs | @@BATTERY@@ |
| `tests/negative_controls.py` — the battery must fail on a broken detector | @@CONTROLS@@ |
| `tests/adversarial.py` — written by a reviewer who did not write the fixes | @@ADVERSARIAL@@ |

@@CI@@ These scores describe the cases executed, not inputs nobody tried.

## Send a result

[`RESULTS.md`](RESULTS.md) is for measurements made by someone other than the author. It is still
empty. `closure-drift --json > result.json`, then
[open an issue](https://github.com/luizfnsilva/closure_drift/issues/new?template=measurement-result.yml)
or write to lfnsilva.invest@gmail.com. A result showing the tool is wrong is the most useful kind.

## Version

**0.9.0.** Script sha256 `@@SHA@@`.
Against 0.7.1, over the seven repositories above: same verdicts, same counts. What changed and what
is no longer comparable: [`CHANGELOG.md`](CHANGELOG.md).

Apache-2.0. Cite the version DOI, under concept DOI `10.5281/zenodo.21763931`
([`CITATION.cff`](CITATION.cff)). Planned next: [`ROADMAP.md`](ROADMAP.md).
