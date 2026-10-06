# Record of the battery runs — closure_drift 1.0.0

Detector 1.0.0: `closure_drift.py`, sha256 `74309fe6db463a53e2dce112596b425a596a1a38dce413054e2db32a23f99f0d`. CI run 37506080583.

| platform | CPython | battery | mutants | adversarial | oracle | properties |
|---|---|---|---|---|---|---|
| Ubuntu | 3.9, 3.10, 3.11, 3.12, 3.13, 3.14 | 161 · 161 green · 0 red · 0 not run | 40 of 40 | 315 · 303 as required · 3 loose · 9 not run | 147 of 147 | 17 of 17 · 10 of 10 controls |
| macOS | 3.10, 3.14 | 161 · 160 green · 0 red · 1 not run | 40 of 40 | 315 · 303 · 3 loose · 9 not run | 147 of 147 | 17 of 17 · 10 of 10 |
| Windows | 3.9, 3.14 | 161 · 156 green · 0 red · 5 not run | 40 of 40 | 315 · 280 · 3 loose · 32 not run | 147 of 147 | 17 of 17 · 10 of 10 |

The 3 loose are ZA02, ZA04, ZX03 on every platform, in the campaign's closed list of known cases
(`docs/FAILURES.md` O2a–O2c, declared in `SCOPE.md`). Not run: as for 0.10.0 below, plus on
Windows the cases of extension 4 that need a POSIX shell or file names Windows refuses.

Regression corpus (`tools/regression/`), the same script: 100 of 100 match. Benchmark run 3, the
same script: `tools/benchmark/READING.md`.

# Record of the battery runs — closure_drift 0.10.0

Detector 0.10.0: `closure_drift.py`, sha256 `91ecd5d1437632b3db65fe606b39b3c924351ac555eb4d5b2704d33785065990`.

## macOS 26.7 (Apple silicon), git 2.54.0 — 2026-10-06

| suite | CPython 3.14.7 |
|---|---|
| `tests/battery.py` | 145 declared · 144 green · 0 red · 1 not run (the same under 3.9.6) |
| `tests/negative_controls.py` | 35 mutants · 35 caught · 0 not caught · positive control holds |
| `tests/adversarial.py` | 275 attacks · 263 as required · 3 loose · 9 not run; the 3 loose are ZA02, ZA04, ZX03, published as `docs/FAILURES.md` O2b, O2a, O2c |
| `tests/oracle.py --self-test` | 117 of 117 |
| `tests/properties.py` | 17 · 17 green · 0 red; 10 controls · 10 caught |

## Linux, macOS, Windows — CI run 37405328391

| platform | CPython | battery | mutants | adversarial | properties |
|---|---|---|---|---|---|
| Ubuntu | 3.9, 3.11, 3.13 | 145 · 145 green · 0 red · 0 not run | 35 of 35 | 275 · 263 as required · 3 loose · 9 not run | 17 of 17 · 10 of 10 controls |
| macOS | 3.11, 3.13 | 145 · 144 green · 0 red · 1 not run | 35 of 35 | 275 · 263 · 3 loose · 9 not run | 17 of 17 · 10 of 10 |
| Windows | 3.9, 3.13 | 145 · 140 green · 0 red · 5 not run | 35 of 35 | 275 · 242 · 3 loose · 30 not run | 17 of 17 · 10 of 10 |

The released script and the build that measured study run 3 and benchmark run 2 (`08ceb754…`),
2026-10-06, on macOS: the same JSON report, apart from `detector_closure`, for the 60 generated
repositories of the property suite, and for `click`, `requests`, `packaging`, `httpx`,
`impress.js` and `lodash` at the default range, at every tag and with `--would-tag` (18 of 18).

The 3 loose are the same three on every platform. What does not run on each platform is listed
under 0.9.0 below, plus, on Windows, the cases of extension 3 that need a POSIX shell or file names
Windows refuses.

# Record of the battery runs — closure_drift 0.9.1

Detector 0.9.1: `closure_drift.py`, sha256 `89b5349928eba22b0394d01940ed3d4aa989d6820f48fdddf189ad521689c51c`.
It differs from 0.9.0 in `__version__` and in three calls of `matches` (`fnmatch.fnmatch` →
`fnmatch.fnmatchcase`), which are the same function on Linux and macOS.

## 0.9.1 — macOS 26.7 (Apple silicon), git 2.54.0, CPython 3.14.7 — 2026-10-05

| suite | result |
|---|---|
| `tests/battery.py` | 120 declared · 119 green · 0 red · 1 not run (also under CPython 3.9.6) |
| `tests/negative_controls.py` | 26 mutants · 26 caught · 0 not caught · positive control holds |
| `tests/adversarial.py` | 235 attacks · 229 as required · 0 loose · 6 not run |
| `tests/properties.py` | 17 properties · 17 green · 0 red · 0 not run; 10 controls · 10 caught |

Mutant M20 was anchored on a line the fix changed; it no longer applied and the controls reported
it as not caught, as they must. It was re-anchored to the new text and nothing else was touched.

0.9.0 against 0.9.1, same machine: the JSON report is identical apart from `detector_closure` for
the 60 generated repositories of the property suite and, at the default range, at every tag and
with `--would-tag`, for `click`, `requests`, `packaging`, `httpx`, `impress.js` and `lodash`.

## 0.9.1 — Linux, macOS, Windows — CI run 37372951536 (`a4cfd8c`)

| platform | CPython | battery | mutation controls | adversarial | properties |
|---|---|---|---|---|---|
| Ubuntu | 3.9, 3.11, 3.13 | 120 declared · 120 green · 0 red · 0 not run | 26 of 26 caught | 235 · 229 as required · 0 loose · 6 not run | 17 of 17 green · 10 of 10 controls |
| macOS | 3.11, 3.13 | 120 · 119 green · 0 red · 1 not run | 26 of 26 caught | 235 · 229 as required · 0 loose · 6 not run | 17 of 17 green · 10 of 10 controls |
| Windows | 3.9, 3.13 | 120 · 115 green · 0 red · 5 not run | 26 of 26 caught | 235 · 209 as required · 0 loose · 26 not run | 17 of 17 green · 10 of 10 controls |

What does not run on each platform is the same as for 0.9.0, below. Two jobs of this run were
cancelled by the runner before they started and were run again; they are the rows above.

Properties and the oracle have their own record: `tests/PROPERTIES_RECORD.md`.

# Record of the battery runs — closure_drift 0.9.0

Kept as written for 0.9.0.

What was run, where, and what did not run. Engineering evidence about the behaviour tested; it is
not a validation of the study in `tools/study/`, which stands on its own protocol.

Detector: `closure_drift.py`, sha256 `6548f891a826034c35ef83b276578c79564b57f892a54422af5c1be44591137c`.

## macOS 26.7 (Apple silicon), git 2.54.0 — 2026-10-04

| battery | CPython 3.14.7 | CPython 3.9.6 |
|---|---|---|
| `tests/battery.py` | 120 declared · 119 green · 0 red · 1 not run | 120 declared · 119 green · 0 red · 1 not run |
| `tests/negative_controls.py` | 26 mutants · 26 caught · 0 not caught · positive control holds | the same |
| `tests/adversarial.py` | 235 attacks · 229 as required · 0 loose · 6 not run | 235 attacks · 228 as required · 0 loose · 7 not run |
| `examples/demo.py`, `tests/fixture_label_only.py` | pass | — |

Repeat runs: the battery's result body is byte-identical across both interpreters and a second run
(sha256 `a0321e1bdb2c1d1f…`). The campaign's body is identical on a second run under 3.14
(`7c5e8289043ee3c9…`) and differs under 3.9 only in the case LC07.

## What did not run, and why

| case | reason |
|---|---|
| battery C06 | macOS refuses a file name that is not valid UTF-8 (runs on Linux) |
| AF07 | the file system stores one normalised name; NFC/NFD twins cannot be staged |
| LT16 | declared limit: labels are compared as written (`v1.0` and `v1.0.0` are two labels) |
| TV03, TV04, TF03, MX05 | superseded; each names what superseded it in `PREREGISTRATION_ADVERSARIAL.md` |
| LC07 (3.9 only) | compares 3.9 with 3.14; under 3.9 it would compare the interpreter with itself |

Command-execution cases: 16 carry a positive control. Under plain git the configured command runs
in 4 of them on this machine, and in each of those it does not run under the detector. In the other
12 no plain git command of the kind the detector uses runs it either.

## Linux, Windows and macOS — CI runs 37238307939 (`3e764e4`) and 37242335850 (`5fbc8d0`), same detector

| platform | CPython | battery | mutation controls | adversarial |
|---|---|---|---|---|
| Ubuntu | 3.9, 3.11, 3.13 | 120 declared · 120 green · 0 red · 0 not run | 26 of 26 caught | 235 · 229 as required · 0 loose · 6 not run |
| macOS | 3.11, 3.13 | 120 · 119 green · 0 red · 1 not run | 26 of 26 caught | 235 · 229 as required · 0 loose · 6 not run |
| Windows | 3.9, 3.13 | 120 · 115 green · 0 red · 5 not run | 26 of 26 caught | 235 · 209 as required · 0 loose · 26 not run |

Linux is the only platform where every proof runs: C06, a file name that is not valid UTF-8,
passes there.

**Windows, battery, 5 not run**: C02, C03, X03, CMP06 (the file system refuses a tab, a line break
or an escape in a file name) and C06 (file names are not byte strings there).

**Windows, adversarial**: in the first run MX01 and LT17 were loose, both the harness — they
compare output byte for byte, and Windows writes a line end as `\r\n`. The harness now reads that
pair as a line end; the detector was not changed, and the second run has no loose case. The 26 not
run there need a POSIX shell, symbolic links or file names Windows refuses; each names its reason
in the CI log.

**Command execution, measured on each platform**: with plain git the configured command runs in 4
of the 16 cases on Linux and macOS, and in 3 or 4 on Windows (one vector fires on one of the two
Windows jobs and not the other). In every case where it runs under plain git, it does not run under
the detector.

## Not measured

Network file systems, repositories with hundreds of thousands of files, git older than 2.24.
Nobody outside the author has run these batteries.

## Reproduce

```bash
./reproduce.sh
```
