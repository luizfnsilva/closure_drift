# Record — properties and oracle

Detector: 0.9.0, sha256 `6548f891a826034c35ef83b276578c79564b57f892a54422af5c1be44591137c`.
Engineering evidence about the relations tested, on generated repositories. Not added to any
other score.

## The oracle

`tests/oracle.py` was written on 2026-10-05 from `tests/ORACLE_SPEC.md` alone, by a reviewer
instructed not to open `closure_drift.py` nor any other test, and who reported having opened
neither. It does not use `fnmatch` for the closure globs. Its own check: 101 of 101.

The reviewer listed twenty places where the specification was silent. Two changed a name and are
Amendment 1 of the specification. The others stand as chosen; those that matter to a comparison:

- a tag that does not point at a commit is counted as such whether or not it matches `--tags`
  (the detector applies `--tags` first); the suite does not compare that count under `--tags`
- an empty closure has the id of empty input, not `null`; the suite compares ids only where
  there are files
- a backslash in a glob is an ordinary character; a reversed range matches nothing. No glob of
  the suite uses either, so the detector is **not tested** on them here

## First run, as it came out — macOS, 2026-10-05

`17 properties · 15 green · 2 red` (PR06, PR07). Both reds were the harness, and the detector was
not changed:

| what was wrong | in | found by |
|---|---|---|
| `git init` sets `core.ignorecase` on macOS; fast-import then filed `Lib/x` under `lib/`, so the generated repository had no case twins and would have differed on Linux | generator | PR06 could not find a path of the model in the repository |
| fast-import refuses a submodule pointer whose id names a blob; that commit is now written through an index | generator | PR06 |
| PR06 picked the version file as the member to remove; the new tag then has no label and `--explain` rightly refuses | PR06 | seed 51 |
| on Windows git refuses the path `q?.js` unless `core.protectNTFS` is off; the suite stopped before any property ran (first CI run, 37347048205) | generator | the Windows jobs |
| a property that could not be evaluated counted as a control caught (K02), and a control on PR13 ran no property at all (K08) | controls | reading the first control table |

## Amendments to the pre-registration — 2026-10-05, after the first run

1. **PR16 strengthened.** As written it could not fail when `--strict` is ignored: K07 was not
   caught. It now also requires the oracle's verdict and exit code under `--strict`.
2. **PR06** reads "one member other than the version file".
3. **K09** is two replacements (sort by name, and first closure wins), as its sentence says.

## Result after the corrections

| platform | properties | controls |
|---|---|---|
| macOS 26.7, git 2.54.0, CPython 3.14.7 | 17 · 17 green · 0 red · 0 not run | 10 · 10 caught · 0 not caught |
| the same, CPython 3.9.6, seeds 0–11 | 17 green | — |

PR06 and PR07 found a case in 41 of 60 seeds, PR12 in 48; the others in all 60. PR15 covers
seeds 0–9.

## Linux, macOS, Windows — CI run 37355181714 (`0.9.0`, same detector)

| platform | CPython | properties | controls |
|---|---|---|---|
| Ubuntu | 3.9, 3.11, 3.13 | 17 · 17 green · 0 red | 10 of 10 caught |
| macOS | 3.11, 3.13 | 17 · 17 green · 0 red | 10 of 10 caught |
| Windows | 3.9, 3.13 | 17 · 13 green · **4 red** (PR01, PR02, PR15, PR16) | not reached |

**The suspicion written before running is confirmed, and it is the detector.** On Windows 0.9.0
matches closure globs without regard to case (`fnmatch.fnmatch` folds case there), so a commit
holding `Lib/data.txt` or `a.PY` has another closure than on Linux and macOS: PR02 differs in 23 of
60 generated repositories, PR01 in 17, and in two (PR16, seeds 13 and 46) the verdict itself
differs — `drift` on Windows where the oracle, and the detector elsewhere, say `empty_closure`.
The oracle reproduces the recorded constants on all three platforms (PR15); the detector does not
on Windows.

Committed as found, before any change to the detector.

## Reproduce

```bash
python3 tests/oracle.py --self-test && python3 tests/properties.py && python3 tests/properties.py --controls
```
