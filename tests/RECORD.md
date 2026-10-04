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

## Not measured here

Linux and Windows: see the CI runs of the commit that carries this file. Network file systems,
repositories with hundreds of thousands of files, git older than 2.24.

## Reproduce

```bash
python3 tests/battery.py && python3 tests/negative_controls.py && python3 tests/adversarial.py
```
