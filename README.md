# closure_drift

**Does `v1.4.2` mean one thing in your repository?**

```
$ closure-drift lodash
DRIFT: 69 of 78 labels name more than one closure
at a publication point. The worst covers 4.
```

When you publish something and address it by its version, that address is sound only if the
version names exactly one state of the code. Nothing enforces it — the version is a string a human
edits. When two releases share a version and differ in code, one address denotes two artefacts, and
**the system cannot notice, because the version is the only thing it recorded.**

One command tells you whether it is happening to you. Read-only, zero dependencies, one file, no
network, nothing written to your repository.

## Run it — 30 seconds

```bash
pipx run closure-drift            # or: uvx closure-drift
```

or, with nothing installed but Python 3.9+ and git:

```bash
curl -sO https://raw.githubusercontent.com/luizfnsilva/closure_drift/v0.8.0/closure_drift.py
python3 closure_drift.py
```

Run it inside any git repository. It reads your tags, finds your version file, and answers.

Not sure what it would tell you? `python3 examples/demo.py`, in the source repository, builds three
tiny repositories in a temporary folder and shows the three answers — clean, drift, and *not enough
to tell* — next to what each should be. One minute, nothing downloaded.

## Use it as a gate — before the tag, not after

`--would-tag` answers one question about the commit you are on: **if I tag this now, does its
version already name different code at an existing tag?** It is the check that stops the most
common cause of drift — a release tagged without bumping the version.

GitHub Actions:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0          # the tags are the publication points
- uses: luizfnsilva/closure_drift@v0.8.0
```

pre-commit (runs on `git push`):

```yaml
- repo: https://github.com/luizfnsilva/closure_drift
  rev: v0.8.0
  hooks:
    - id: closure-drift-would-tag
```

Anywhere else: `closure-drift --would-tag` exits `1` when the tag would create drift.

## What the answer means

| verdict | exit | meaning |
|---|---|---|
| `clean` | `0` | every label names exactly one closure, over the points compared |
| `drift` | `1` | at least one label names more than one closure at a publication point |
| `inconclusive` | `2` | only one distinct label in the range: nothing to compare it with |
| `incomplete` | `2` | no drift, but `--strict` was asked for and some points could not be compared |
| `no_labels`, `empty_closure`, `no_publication_points` | `2` | no version, no file in the closure, or no tag was found — the report says which |
| *(a refusal)* | `2` | the cause is named on stderr: not a repository, broken config, bad pattern, git failed |

With `--would-tag`: `would_be_clean` `0` · `would_drift` `1` · `no_label_at_head`,
`empty_closure_at_head` `2`.

**Exit `0` means `clean` and nothing else.** An absence of measurement is never a pass, no input
produces a traceback, and no failure ends at `1`. *(Changed in 0.8.0: up to 0.7.1 `inconclusive`
and `no_labels` also ended at `0`.)*

The two things compared at each **publication point**:

| | |
|---|---|
| **label** | the version you declare, read from your version file at that point |
| **closure** | SHA-256 over `(path, git object id)` of the files that determine your output |

Every report also says what it did **not** compare: tags that declare no version, tags where the
closure is empty, tags outside `--max-commits`. A `clean` over 11 of 71 tags is a different claim
from a `clean` over all of them, and the report prints the count.

## Options

| | |
|---|---|
| `--would-tag` | before tagging: would this commit reuse a label that names other code? |
| `--tags 'v*'` | only tags matching the glob are publication points (repeatable). For monorepos that release several packages from one version file under tag families such as `py-*` and `rs-*` |
| `--at commits` | you publish continuously — a feed, a site, a daily edition: every commit is a point |
| `--closure 'src/**'` | which files determine your output (repeatable). The defaults are a guess; the report prints what was used |
| `--strict` | `clean` only if every point scanned was compared; otherwise `incomplete` |
| `--explain LABEL` | for a label in drift, list the paths that differ. Only on request: the report otherwise names no file of yours |
| `--version-file`, `--version-regex` | where the label is, when it is not found automatically |
| `--max-commits N` | the most recent N points (default 400) |
| `--json` | the machine-readable report (`report_format: 2`); its fields and compatibility rules are a contract, in `docs/REPORT.md` of the source repository |
| `--badge` | one line of Markdown — see below |

A repository can commit its own settings in `.closure-drift.json`, so that the command with no flags
measures it the way it declares it should be measured:

```json
{"at": "tags", "tags": ["py-*"], "version_file": "py/pyproject.toml",
 "version_regex": "^version\\s*=\\s*\"([^\"]+)\"", "closure": ["py/src/**"]}
```

Command-line flags override the file. A broken file, or a key the tool does not know, is a refusal —
never silently ignored.

## A badge that says what it measured

```bash
closure-drift --badge
```

prints a line such as `![version labels: clean @ 1ea5e43618b4](https://img.shields.io/badge/…)`.
The badge carries the commit it was measured at, so a stale badge is visibly stale rather than
silently wrong.

## What it found elsewhere

**The 100 most-downloaded PyPI projects, measured at the tool's defaults** (rule and method fixed
before the first measurement, no per-repository tuning, 2026-10-04):

| outcome | repositories |
|---|---|
| `clean` | 42 |
| `drift` | 21 |
| no version label found by the defaults | 34 |
| `inconclusive` / `no_labels` | 3 |

Drift at **21 of the 63** where a determination was reached, and 21 of all 100. Read that number with
its two qualifications. In 7 of the 21 the defaults read a constant string as the version — the
real one comes from the tag — so the finding there is about the defaults, not the project. In the
other 14 the label does move with the releases, and one to six labels name two different trees.
The 42 `clean` verdicts cover 2943 of 4632 tags scanned; the rest declared no version at the tag. Every
row, the selection rule and the reports are in `tools/study/` of the source repository.

Earlier reference measurements, dated, on repositories chosen by the author:

| Repository | Points | Labels | In drift | Worst label | Verdict |
|---|---|---|---|---|---|
| `pallets/click` | 68 tags | 10 | 0 | 1 closure | clean |
| `psf/requests` | 66 tags | 12 | 0 | 1 closure | clean |
| `pypa/packaging` | 17 tags | 13 | 0 | 1 closure | clean |
| `encode/httpx` | 28 tags | 28 | 0 | 1 closure | clean |
| `impress/impress.js` | 15 tags | 4 | 2 | 2 closures | **drift** |
| `lodash/lodash` | 400 of 440 tags | 78 | 69 | 4 closures | **drift** |
| `pola-rs/polars` | 400 of 570 tags | 51 | 40 | 16 closures | **drift** |

*(Measured 2026-08-02 and 2026-08-23 with the 0.3.0 script. On 2026-10-04 the seven were measured
again with 0.7.1 and with this release at the same commits: every verdict field is identical between
the two scripts.)*

Two mechanisms produce drift, and they should be cited as distinct. In `impress.js` it is the simple
forgetting: a release tagged without bumping the version file. In `lodash` and `polars` it is **label
collision across tag families** — variant builds, or a monorepo's `rs-*`/`py-*` releases sharing one
version file. Neither project is badly run; drift is a property of an addressing scheme, not a
defect of character. `--would-tag` addresses the first mechanism, `--tags` the second.

## What it does not do

It answers one question — does the label identify exactly one code state where you publish? — and
stops. It **never runs your code**, so it says nothing about whether rebuilding a version gives the
published bits. It **attests nothing**: no signature, no certificate, no statement a third party is
meant to rely on. `clean` means clean over the range scanned, at the points compared.

Limits worth knowing before you rely on a number:

- The closure is `(path, object id)`. A change of **file mode only** (a file made executable, or
  turned into a symbolic link with the same bytes) is not seen.
- Paths under `test/`, `tests/`, `docs/`, `vendor/`, `node_modules/` and `*.md` are **never** in the
  closure, even when a `--closure` glob matches them. If code that determines your output lives
  there, this tool does not see it change.
- The default closure globs are a guess. Pass `--closure`.

[`SCOPE.md`](SCOPE.md) states the boundary in full; [`docs/WHY.md`](docs/WHY.md), in the source
repository, argues why an unambiguous address is a precondition of reproducibility and not a part of
it.

## What it does to your machine

It starts `git` (`rev-parse`, `for-each-ref`, `rev-list`, `log`, `cat-file`, `config --list`,
`status`) on the repository you point it at, and — only when the version pattern is not one of its
own — itself, once per distinct version file, to match that pattern under a time limit. Nothing
else. No network. It never writes to the repository it measures, and it does not run commands named
by that repository's own git configuration (`core.fsmonitor`, clean filters, replace refs and
`GIT_DIR` in your environment are all neutralised, and each is a tested case). Details and how to
report a vulnerability: [`SECURITY.md`](SECURITY.md).

## Tests

Three batteries, each with its own polarity and its own pre-registration, written before the code
they test. Their scores are reported side by side and **never added together**.

| battery | what it shows | measured on macOS, CPython 3.9 and 3.14 |
|---|---|---|
| `tests/battery.py` | the pre-registered acceptance proofs | 81 declared · 80 green · 0 red · 1 not run |
| `tests/negative_controls.py` | the battery goes red on a broken detector: each mutant must be caught by a named proof | 15 mutants · 15 caught by the required proof · 0 not caught |
| `tests/adversarial.py` | hostile repositories and hostile input, written by a reviewer who did not write the fixes | 85 attacks · 84 as required · 0 loose · 1 not run |

The same three run on every push on Linux, macOS and Windows; a proof the platform cannot stage
comes out `not run` with the reason named, never green. Run against the previous release (0.7.1), the
acceptance battery is red on every defect this release corrects. `fixture_label_only.py`, the
negative fixture deposited since 0.4.0, still ships and still passes.

These scores describe behaviour on the cases executed. They are not a claim about inputs nobody
tried.

## Send a result

Everything in the tables above is the author measuring other people's repositories from the outside.
[`RESULTS.md`](RESULTS.md) is the table for measurements made by someone else, on their own
repository; **it is still empty, and published empty on purpose.**

```bash
closure-drift --json > result.json
```

Open a [**Report a measurement**](https://github.com/luizfnsilva/closure_drift/issues/new?template=measurement-result.yml)
issue with it, or send it to **lfnsilva.invest@gmail.com**. The report carries counts, labels, hashes
and the tool's own stamp — never file contents, and no path inside your closure unless you asked for
`--explain`. A result that contradicts the tool is worth more than one that confirms it, and there is
a [separate form](https://github.com/luizfnsilva/closure_drift/issues/new?template=false-positive.yml)
for it.

## The report stamps itself

```json
"report_format": 2,
"stamp": {
  "measured_at_head": "1ea5e43618b4",
  "working_tree_dirty": false,
  "detector_closure": "1125e51615efc369"
}
```

A count over a repository's history is a function of its `HEAD` and of the detector that counted.
A finding without those two values is a finding you cannot return to.

## Requirements

CPython **3.9 or later** and `git` on `PATH`. No third-party packages, no network, no required
configuration.

## Version

**0.8.0** — see `CITATION.cff` and `CHANGELOG.md`. The measurement script is sha256
`1125e51615efc3698f09e7bce92bc8647eb468db5471ca79b8ee202cef684cda`, against
`6d8906ef374b73e6b8c58adba813c77c4ff352f5c9c280aa43ff2baa4f804451` for 0.7.0–0.7.1 and
`da5da3c0e781b67b9b3a55800d599c243edc8df649fc90b24a88e289533805c5` for 0.3.0–0.6.0.

**What stays comparable, and what does not.** The 16-hex closure of every earlier version is still
computed and printed, by the same formula. Over the seven public repositories of the reference
table, 0.7.1 and 0.8.0 give identical verdict fields. Three kinds of repository can get a different
answer from 0.8.0, and in each the earlier answer was the wrong one: a closure holding a path that is
not plain ASCII (0.7.1 silently left the file out), a closure holding a submodule pointer (ignored
until now), and two file lists that the earlier formula hashed to the same bytes (identity is now
decided by a second, unambiguous, full-length hash). Exit codes changed for `inconclusive` and
`no_labels`, from `0` to `2`. `CHANGELOG.md` has every item, with the measurement that showed it.

## Licence and citation

Apache-2.0, unabridged. See `LICENSE`, and `NOTICE` for the scope of this release. Commercial use is
permitted with **no royalty and no payment obligation**. `CITATION.cff` carries the machine-readable
citation.

Each deposited version has its own DOI under the concept DOI `10.5281/zenodo.21763931`. **Cite the
version DOI** when you report a measurement — the report records which detector produced it, and a
citation that does not pin the version cannot be checked against that record.

The source is at **<https://github.com/luizfnsilva/closure_drift>**, where the files of this deposit
are held byte-identical to it under a checksum gate, and the PyPI package is built from the same
file, checked byte for byte before upload.

## Related

This is the detector for the first of six principles in an article about a production audit. It
comes out of a longer research programme on measuring what a record can and cannot establish about
the thing it records. [`SCOPE.md`](SCOPE.md) marks where this tool stops; work on the far side of
that boundary — re-execution, attestation, delivery verification — exists but is not this tool and
will not arrive as a silent extension of it. If your problem lives there, write.
