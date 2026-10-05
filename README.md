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

- **label** — the version your project declares at each tag: in its build files, in the module
  they point to, or the tag itself when the version is derived from it
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
run; no repository tuned ([full table and every collision](tools/study/STUDY.md)):

| | repositories |
|---|---|
| `clean` | 63 |
| `drift` | 29 |
| no version label found, or inconclusive | 8 |

A version label names two different code states in **29 of the 92** decided, 29 of all 100. Each
of the 87 labels is a line in `collisions.tsv`, reproducible by hand:

```
$ closure-drift --compare v2.16.0 v2.16.1        # in psf/requests
DIFFERS UNDER ONE LABEL: both declare 2.16.0, and the code differs in 2 path(s).
```

A collision is not a verdict on a project. The usual causes are a tag created without bumping the
version, branch markers such as `7.x`, and tag families in a monorepo. A first run, kept in the
repository, decided only 63 of 100 — it read the version from one file chosen at HEAD — and that
is why this release finds the label where each project keeps it.

Seven repositories measured since 0.3.0, with 0.7.1 and with this release:

| Repository | 0.7.1 | 0.9.0 | Tags compared (0.7.1 → 0.9.0) |
|---|---|---|---|
| `pallets/click` | clean | **drift**, 3 of 66 labels | 11 → 71 of 71 |
| `psf/requests` | clean | **drift**, 3 of 140 labels | 12 → 145 of 162 |
| `pypa/packaging` | clean | clean | 14 → 50 of 53 |
| `encode/httpx` | clean | clean | 69 → 88 of 88 |
| `impress/impress.js` | drift, 2 of 4 | drift, 2 of 4 | 6 of 15 |
| `lodash/lodash` | drift, 69 of 78 | drift, 69 of 78 | 280 of 400 |
| `pola-rs/polars` | drift, 41 of 51 | drift, 41 of 51 | 281 of 400 |

`click` and `requests` were `clean` over the dozen tags 0.7.1 could read; read at every tag, three
labels in each name two trees.

Two causes: a release tagged without bumping the version (`impress.js`), and tag families sharing
one version file (`lodash`, `polars`). Neither project is badly run. `--would-tag` addresses the
first, `--tags` the second.

## Limits

- It never runs your code and attests nothing. `clean` is about addressing, not reproducibility.
- A change of file mode alone is not seen.
- `tests/`, `docs/`, `vendor/`, `node_modules/` and `*.md` are never in the closure.
- The default closure globs are a guess. Pass `--closure`.
- Labels are compared as written: `1.0` and `1.0.0` are two labels.
- How the label is found is a set of rules, not a build: [`docs/LABELS.md`](docs/LABELS.md).

More: [`SCOPE.md`](SCOPE.md), [`docs/WHY.md`](docs/WHY.md).

## Safety

It starts `git` and nothing else, never writes to the repository, and does not run commands named
in that repository's git config. Details and reporting: [`SECURITY.md`](SECURITY.md).

## Tests

Three batteries, each pre-registered before the code. Scores are never added together.

| battery | macOS, Python 3.14 (3.9: the same, one more attack not run) |
|---|---|
| `tests/battery.py` — acceptance proofs | 120 declared · 119 green · 0 red · 1 not run |
| `tests/negative_controls.py` — the battery must fail on a broken detector | 26 mutants · 26 caught · 0 not caught |
| `tests/adversarial.py` — written by a reviewer who did not write the fixes | 235 attacks · 229 as required · 0 loose · 6 not run |

CI runs the same three on Linux, macOS and Windows; what each platform could not run is in [`tests/RECORD.md`](tests/RECORD.md). These scores describe the cases executed, not inputs nobody tried.

## Send a result

[`RESULTS.md`](RESULTS.md) is for measurements made by someone other than the author. It is still
empty. `closure-drift --json > result.json`, then
[open an issue](https://github.com/luizfnsilva/closure_drift/issues/new?template=measurement-result.yml)
or write to lfnsilva.invest@gmail.com. A result showing the tool is wrong is the most useful kind.

## Version

**0.9.0.** Script sha256 `6548f891a826034c35ef83b276578c79564b57f892a54422af5c1be44591137c`.
0.9.0 reads the label at every tag, so it compares more tags than 0.7.1 and can find drift 0.7.1
could not see. With `--version-file` it reads one file, as before. What changed and which earlier
results to measure again: [`CHANGELOG.md`](CHANGELOG.md).

Apache-2.0. Cite the version DOI, under concept DOI `10.5281/zenodo.21763931`
([`CITATION.cff`](CITATION.cff)). Planned next: [`ROADMAP.md`](ROADMAP.md).
