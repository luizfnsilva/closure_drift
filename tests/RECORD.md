# Record of the battery runs — closure_drift 1.1.3

Detector 1.1.3: `closure_drift.py`, sha256 `101905f660655bda98303ed5286620d4fd78d782bbe88bfcdd51c4f49ae2c5a4`. CI run 39143740829 (`7edf4b5`).

| platform | CPython | battery | mutants | adversarial | oracle | properties |
|---|---|---|---|---|---|---|
| Ubuntu | 3.9, 3.10, 3.11, 3.12, 3.13, 3.14 | 210 · 210 green · 0 red · 0 not run | 57 of 57 | 315 · 304 as required · 2 loose · 9 not run | 147 of 147 | 17 of 17 · 10 of 10 controls |
| macOS | 3.10, 3.14 | 210 · 209 green · 0 red · 1 not run | 57 of 57 | 315 · 304 · 2 loose · 9 not run | 147 of 147 | 17 of 17 · 10 of 10 |
| Windows | 3.9, 3.14 | 210 · 205 green · 0 red · 5 not run | 57 of 57 | 315 · 281 · 2 loose · 32 not run | 147 of 147 | 17 of 17 · 10 of 10 |

The 2 loose are ZA02 and ZA04 (`docs/FAILURES.md` O2b, O2a). PK01 was red on 1.1.2 (`build/` and
`closure_drift.egg-info/` tracked) and is green here; MCP03 now builds its wheel from a copy, so a
run of the battery leaves no build output in the checkout.

Regression corpus (`tools/regression/`), the same script: 100 of 100 match, as predicted in §19
(run 39137472996, `checks/v1.1.3-candidate-101905f6.json`). The benchmark was not rerun for 1.1.3.

# Record of the battery runs — closure_drift 1.1.2

Detector 1.1.2: `closure_drift.py`, sha256 `a61858aa662385ff3a35703a90ca923522f34c271b1df3568ec5a04a06c31aac`. CI run 38882707497 (`3e02500`).

| platform | CPython | battery | mutants | adversarial | oracle | properties |
|---|---|---|---|---|---|---|
| Ubuntu | 3.9, 3.10, 3.11, 3.12, 3.13, 3.14 | 209 · 209 green · 0 red · 0 not run | 57 of 57 | 315 · 304 as required · 2 loose · 9 not run | 147 of 147 | 17 of 17 · 10 of 10 controls |
| macOS | 3.10, 3.14 | 209 · 208 green · 0 red · 1 not run | 57 of 57 | 315 · 304 · 2 loose · 9 not run | 147 of 147 | 17 of 17 · 10 of 10 |
| Windows | 3.9, 3.14 | 209 · 204 green · 0 red · 5 not run | 57 of 57 | 315 · 281 · 2 loose · 32 not run | 147 of 147 | 17 of 17 · 10 of 10 |

The 2 loose are ZA02 and ZA04 (`docs/FAILURES.md` O2b, O2a). MCP01–MCP03 were red on 1.1.1 (no
server at the repository root, none in the wheel) and are green here; every mutant turns them red
too, since the server runs the mutated script. Two earlier matrices (runs 38817577739 and
38856524013) lost 12 and then 3 of the mutants on macOS py3.10 with no result written: the
battery's own cleanup failed on `.git/objects/maintenance.lock`, which git's background
maintenance adds and removes while the temporary tree is removed. `remove()` now tolerates a file
that vanished and tries again (`3e02500`); the detector did not change. On a pip too old to read
`pyproject.toml` (21.2, the Command Line Tools' 3.9) MCP03 is not run, with the reason.

Regression corpus (`tools/regression/`), the same script: 100 of 100 match, as predicted in §18
(run 38817581615, `checks/v1.1.2-candidate-a61858aa.json`). The benchmark was not rerun for 1.1.2.

# Record of the battery runs — closure_drift 1.1.1

Detector 1.1.1: `closure_drift.py`, sha256 `890616f787db105e7ae0d95c99970da524e385641165b20f11a79d0469e7d9d1`. CI run 38657707944 (the two Windows jobs
rerun once: the hosted runner lost communication during the property step, after the battery,
mutants, adversarial campaign and oracle had passed).

| platform | CPython | battery | mutants | adversarial | oracle | properties |
|---|---|---|---|---|---|---|
| Ubuntu | 3.9, 3.10, 3.11, 3.12, 3.13, 3.14 | 206 · 206 green · 0 red · 0 not run | 57 of 57 | 315 · 304 as required · 2 loose · 9 not run | 147 of 147 | 17 of 17 · 10 of 10 controls |
| macOS | 3.10, 3.14 | 206 · 205 green · 0 red · 1 not run | 57 of 57 | 315 · 304 · 2 loose · 9 not run | 147 of 147 | 17 of 17 · 10 of 10 |
| Windows | 3.9, 3.14 | 206 · 201 green · 0 red · 5 not run | 57 of 57 | 315 · 281 · 2 loose · 32 not run | 147 of 147 | 17 of 17 · 10 of 10 |

The 2 loose are ZA02 and ZA04 (`docs/FAILURES.md` O2b, O2a). LG01 and LG02 were red on 1.1.0
(`clean` and `would_be_clean`, exit 0, over a label not read) and are green here; M57 turns LG01,
LG02, LG06 and LG07 red. An earlier matrix (run 38610371098) found ZM06 loose on macOS with a 10 MB
limit; the limit went back to 1 MB (§17 amendment 2). A first run found M34 no longer applying
after the O11 change of its line; it was re-anchored, the mutation unchanged.

Regression corpus (`tools/regression/`), the same script: 100 of 100 match, as predicted in §17
(run 38657710757). The benchmark was not rerun for 1.1.1.

# Record of the battery runs — closure_drift 1.1.0

Detector 1.1.0: `closure_drift.py`, sha256 `e2a67a5a9148fe273d2c95ad4bcce9bc589a43711fc34443a4a9491fde575913`. CI run 37976952891.

| platform | CPython | battery | mutants | adversarial | oracle | properties |
|---|---|---|---|---|---|---|
| Ubuntu | 3.9, 3.10, 3.11, 3.12, 3.13, 3.14 | 199 · 199 green · 0 red · 0 not run | 56 of 56 | 315 · 304 as required · 2 loose · 9 not run | 147 of 147 | 17 of 17 · 10 of 10 controls |
| macOS | 3.10, 3.14 | 199 · 198 green · 0 red · 1 not run | 56 of 56 | 315 · 304 · 2 loose · 9 not run | 147 of 147 | 17 of 17 · 10 of 10 |
| Windows | 3.9, 3.14 | 199 · 194 green · 0 red · 5 not run | 56 of 56 | 315 · 281 · 2 loose · 32 not run | 147 of 147 | 17 of 17 · 10 of 10 |

The 2 loose are ZA02 and ZA04 (`docs/FAILURES.md` O2b, O2a); ZX03 (O2c) is now as required. The
review's findings R1–R13 are in `docs/REVIEW-1.1.0.md`; their proofs (PUB12, RV01–RV11) were red
on the candidate before the fixes. A first matrix (run 37973430775) found mutant M14 no longer
applying after a change of `closure.ids()`; it was re-anchored, the mutation unchanged.

Regression corpus (`tools/regression/`), the same script: 100 of 100 match, as predicted in §16
(`checks/v1.1.0-candidate-e2a67a5a.json`). The benchmark was not rerun for 1.1.0.

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
