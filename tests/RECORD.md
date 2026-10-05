# Record of the battery runs — closure_drift 0.9.0

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
python3 tests/battery.py && python3 tests/negative_controls.py && python3 tests/adversarial.py
```
