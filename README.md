# closure_drift

**Does `v1.4.2` mean one thing in your repository?**

```
$ closure-drift lodash
DRIFT: 60 of 67 labels name more than one closure
at a publication point. The worst covers 3.
```

A version is a string a human edits. When two releases share a version and differ in code, one
address names two artefacts — and nothing notices, because the version is all that was recorded.

One command checks it. Read-only, one file, no dependencies, no network.

## Run it

```bash
curl -sO https://raw.githubusercontent.com/luizfnsilva/closure_drift/v1.0.0/closure_drift.py
python3 closure_drift.py            # inside any git repository
```

or `pipx run --spec git+https://github.com/luizfnsilva/closure_drift@v1.0.0 closure-drift`.
Needs Python 3.9+ and git. To see the three possible answers first: `python3 examples/demo.py`, or read [`docs/DEMOS.md`](docs/DEMOS.md).

## Check before you tag

`--would-tag` answers: *if I tag this commit now, does its version already name different code?*

```yaml
# GitHub Actions
- uses: actions/checkout@v4
  with: { fetch-depth: 0 }
- uses: luizfnsilva/closure_drift@v1.0.0
```

```yaml
# pre-commit, on git push
- repo: https://github.com/luizfnsilva/closure_drift
  rev: v1.0.0
  hooks: [{ id: closure-drift-would-tag }]
```

Other pipelines: [`docs/CI.md`](docs/CI.md).

## The answer

| verdict | exit | |
|---|---|---|
| `clean` | 0 | every label names one closure, over at least as many points compared as not |
| `drift` | 1 | a label names more than one closure |
| any other verdict ([list](docs/REPORT.md)) | 2 | not enough to tell; the report says why |
| refusal | 2 | cause on stderr |

Exit 0 means `clean` and nothing else. No input we tried produces a traceback, and no failure exits 1.

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
| `--component NAME` | one component of a monorepo (below) |
| `--json`, `--badge`, `--diagnose` | report ([contract](docs/REPORT.md)), README badge, bug-report block |

Settings can be committed in `.closure-drift.json`. Flags override it, except beside `components`,
where they need `--component`; a broken file is refused.

A monorepo declares its components, and gets one verdict each:

```json
{"components": {
  "python": {"tags": ["py-*"], "version_file": "py/pyproject.toml", "closure": ["py/**"]},
  "rust":   {"tags": ["rs-*"], "version_file": "rs/Cargo.toml",     "closure": ["rs/**"]}
}}
```

The answer is `drift` if any component is in drift, `clean` if all are clean, otherwise
`incomplete`. Components are declared, never guessed. A gate in such a repository passes
`--component NAME` to `--would-tag`.

## What it found

**The 100 most-downloaded PyPI projects with a public repository, at the defaults**, measured with a build of 0.10.0 that prints
the same reports as the release — rule and method
fixed before the first run; no repository tuned ([full table and every collision](tools/study/STUDY.md)):

| | repositories |
|---|---|
| `clean` | 59 |
| `drift` | 29 |
| `incomplete` — fewer tags compared than not | 4 |
| no version label found, or inconclusive | 8 |

A version label names two different code states in **29 of the 88** decided, 29 of all 100. Each
of the 87 labels is in `collisions.tsv`, one line per tag involved, reproducible by hand:

```
$ closure-drift --compare v2.16.0 v2.16.1        # in psf/requests
DIFFERS UNDER ONE LABEL: both declare 2.16.0, and the code differs in 2 path(s).
```

A collision is not a verdict on a project. The usual causes are a tag created without bumping the
version, branch markers such as `7.x`, and tag families in a monorepo. A first run, kept in the
repository, decided only 63 of 100 — it read the version from one file chosen at HEAD — and that
is why this release finds the label where each project keeps it.

Six reference repositories, measured with 1.0.0 at every tag ([`tools/reference/`](tools/reference/)):

| Repository | verdict | labels in drift | tags compared |
|---|---|---|---|
| `pallets/click` | drift | 3 of 66 | 71 of 71 |
| `psf/requests` | drift | 3 of 140 | 145 of 162 |
| `pypa/packaging` | clean | 0 of 50 | 50 of 53 |
| `encode/httpx` | clean | 0 of 88 | 88 of 88 |
| `impress/impress.js` | drift | 2 of 4 | 6 of 15 |
| `lodash/lodash` | drift | 60 of 107 | 209 of 440 |

Two causes: a release tagged without bumping the version (`impress.js`), and tag families sharing
one version file (`lodash`). Neither project is badly run. `--would-tag` addresses the first,
`--tags` or components the second.

## Limits

- It never runs your code and attests nothing. `clean` is about addressing, not reproducibility.
- A change of file mode alone is not seen.
- Never in the closure: folders `test/`, `tests/`, `spec/`, `docs/`, `vendor/`, `node_modules/`,
  `.git/`; files named `*_test.*`, `*.test.*`, `*.md`.
- The default closure globs are a guess. Pass `--closure`.
- Labels are compared as written: `1.0` and `1.0.0` are two labels.
- How the label is found is a set of rules, not a build: [`docs/LABELS.md`](docs/LABELS.md).

- In a gate, pass `--version-file`: the rules can still read the wrong file when one tag happens to
  agree with it.

Every failure found so far: [`docs/FAILURES.md`](docs/FAILURES.md). More: [`SCOPE.md`](SCOPE.md),
[`docs/WHY.md`](docs/WHY.md).

## Safety

It starts `git` and, for a version pattern you supply, itself; nothing else. It never writes to the repository, and does not run commands named
in that repository's git config. What is defended and what is not:
[`THREAT_MODEL.md`](THREAT_MODEL.md). Reporting: [`SECURITY.md`](SECURITY.md).

## Tests

Four suites, each pre-registered before the code. Scores are never added together.

| suite | macOS, Python 3.14 |
|---|---|
| `tests/battery.py` — acceptance proofs | 161 declared · 160 green · 0 red · 1 not run |
| `tests/negative_controls.py` — the battery must fail on a broken detector | 40 mutants · 40 caught · 0 not caught |
| `tests/adversarial.py` — written by reviewers who did not write the fixes | 315 attacks · 303 as required · 3 loose · 9 not run; the 3 loose are declared limits ([`docs/FAILURES.md`](docs/FAILURES.md) O2a–O2c) |
| `tests/properties.py` — 60 generated repositories against `tests/oracle.py`, a second implementation written from a specification by someone who did not read this one | 17 properties · 17 green · 0 red · 10 controls · 10 caught |

CI runs the same four on Linux (Python 3.9 to 3.14), macOS and Windows; what each platform could not
run is in
[`tests/RECORD.md`](tests/RECORD.md). These scores describe the cases executed, not inputs nobody
tried. `./reproduce.sh` runs all of it. The 100 projects of the study are also a regression corpus,
pinned to recorded commits: 1.0.0 gives the recorded answer on all 100
([`tools/regression/`](tools/regression/)).

**Ten large repositories** (the Linux kernel, LLVM, CPython and seven more), protocol written
first. Every tag of the kernel: 6.5 GB for the whole process tree with 0.9.1, 900 MB with 1.0.0.
0.9.1 gave three wrong or near-empty answers there; 1.0.0 gives none of them. With a declared
version file ([`docs/LABELS.md`](docs/LABELS.md)) every tag of the kernel is compared: `clean`,
947 of 947, in four minutes.
[`tools/benchmark/READING.md`](tools/benchmark/READING.md).

## Send a result

[`RESULTS.md`](RESULTS.md) is for measurements made by someone other than the author. It is still
empty. `closure-drift --json > result.json`, then
[open an issue](https://github.com/luizfnsilva/closure_drift/issues/new?template=measurement-result.yml)
or write to lfnsilva.invest@gmail.com. A result showing the tool is wrong is the most useful kind.

## Version

**1.0.0.** Script sha256 `74309fe6db463a53e2dce112596b425a596a1a38dce413054e2db32a23f99f0d`.
1.0 adds nothing to impress: every open item that could give a wrong answer is fixed or declared
in [`SCOPE.md`](SCOPE.md), which also says what stays stable until 2.0. What it had to meet was
written first ([`tests/PREREGISTRATION.md`](tests/PREREGISTRATION.md) §11).
[`CHANGELOG.md`](CHANGELOG.md).

Apache-2.0. Cite the version DOI, under concept DOI `10.5281/zenodo.21763931`
([`CITATION.cff`](CITATION.cff)). Planned next: [`ROADMAP.md`](ROADMAP.md).
