# Pre-registration — properties, and an oracle that did not read the detector

Written 2026-10-05, before `tests/properties.py`, before `tests/oracle.py`, and before either was
run. Detector under test: 0.9.0 as deposited, sha256
`6548f891a826034c35ef83b276578c79564b57f892a54422af5c1be44591137c`.

## Why

The battery and the campaign test cases someone thought of. This suite tests relations that must
hold for every repository, on repositories nobody wrote by hand, and compares the detector with a
second implementation written from a specification (`tests/ORACLE_SPEC.md`) by someone who did not
read the detector.

## Repositories

Generated from a seed, with `git fast-import`, bare, no working tree — so the same bytes exist on
Linux, macOS and Windows, including names a file system would refuse. Each has 2–8 tags, 5–40
files up to four folders deep, a version file with labels drawn from a small pool so that labels
repeat, and between commits: content changes, files added and removed, mode changes, symbolic
links, submodule pointers. Names include upper and lower case twins (`Lib/`, `lib/`, `a.PY`),
excluded folders, spaces, non-ASCII, glob characters, a tab, a line break and a byte that is not
UTF-8. Closure globs are the defaults or drawn from a fixed pool.

Seeds: 0 to 59. The version file and its pattern are always given, so no label heuristic takes part.

## Properties

Each holds for every seed, or the property is red and the seed is printed.

| id | statement |
|---|---|
| PR01 | A full run agrees with the oracle: verdict, exit code, every count, the set of labels in drift and the full closure ids under them |
| PR02 | `--compare` on two tags agrees with the oracle: both full ids, both file counts, the three path lists |
| PR03 | The same command twice prints the same bytes and ends with the same code |
| PR04 | A bare clone of the repository gives the same report, apart from the `repo` field |
| PR05 | Adding, changing and removing files outside the closure at every commit changes no closure id and no verdict |
| PR06 | Under a label that names one closure, a new tag with that label and one member changed, added, removed, or turned from file into submodule pointer gives `drift`, and `--explain` names that path and no other |
| PR07 | Declared limit, tested as a limit: the same with only a file mode changed gives no new closure |
| PR08 | Permuting the creation dates of the tags changes neither the verdict, nor the set of labels in drift, nor the closure ids under them |
| PR09 | Renaming every tag changes neither the verdict nor any count nor any closure id |
| PR10 | `--compare A B` and `--compare B A` give the same verdict and `changed`, with `only_in_a` and `only_in_b` exchanged; `--compare A A` is `identical` when A has a closure |
| PR11 | Removing one tag never adds a label to the set in drift |
| PR12 | `--would-tag` says `would_drift` exactly when, after tagging HEAD, the label of HEAD is in drift; `would_be_clean` exactly when it is not |
| PR13 | Over every run this suite makes: the exit code is 0, 1 or 2; it is 0 exactly for `clean`, `would_be_clean`, `identical`, `differs_under_two_labels`; 1 exactly for `drift`, `would_drift`, `differs_under_one_label`; stderr never holds `Traceback` nor `internal error` |
| PR14 | The repository named by a relative path, an absolute path, and with a trailing separator gives the same report apart from `repo` |
| PR15 | For seeds 0–9, the commit ids and the oracle's closure ids equal the constants in `tests/properties_expected.json`, written once on macOS from the oracle — on every platform, for the oracle and for the detector |
| PR16 | `--strict` never turns a verdict into `clean`; it changes only `clean` into `incomplete` |
| PR17 | `--tags GLOB` gives the verdict, counts and closure ids of the same repository holding only the tags that match |

## Controls

A property that cannot fail guards nothing. `tests/properties.py --controls` breaks the detector in
the ways below, one at a time, by text replacement on a copy; each must turn the named property
red. A replacement that does not apply counts as a failed control.

| id | break | must turn red |
|---|---|---|
| K01 | `**/docs/**` removed from the exclusions | PR01 or PR05 |
| K02 | the full id leaves out the entry type | PR06 |
| K03 | paths are matched without regard to case | PR01 or PR15 |
| K04 | `only_in_a` and `only_in_b` are exchanged in `--compare` | PR02 or PR10 |
| K05 | `--would-tag` compares with the same closure instead of the different ones | PR12 |
| K06 | `--tags` keeps the tags that do not match | PR17 |
| K07 | `--strict` is ignored | PR16 |
| K08 | `inconclusive` exits 0 | PR13 |
| K09 | tags are scanned in name order and the first closure of a label wins | PR01 or PR08 |
| K10 | submodule pointers are left out of the closure | PR01 |

## Disagreement with the oracle

A disagreement is not assumed to be the detector's fault. It is committed as found, then read:
the specification said something the detector does not do (the specification is corrected, dated,
and the difference is written down), the oracle is wrong, or the detector is wrong. The third kind
goes to `docs/FAILURES.md`.

## What is suspected before running

`fnmatch.fnmatch` folds case on Windows. If so, `Lib/data.txt` is in the default closure there and
not on Linux, and one commit has two closure ids depending on where it is measured. PR01 and PR15
on the Windows runner will say. Written here so that the result cannot be told as a surprise.

## Score

`properties · green · red · not run`, and `controls · caught · not caught`, per platform, never
added to the other batteries.

## Amendment — 2026-10-05, after the Windows run and before the detector is changed

Amendments 1–3 are in `tests/PROPERTIES_RECORD.md`. This one is about the detector.

The Windows run confirmed the suspicion above. The change, written before it is made: in
`matches`, the three calls to `fnmatch.fnmatch` become `fnmatch.fnmatchcase`. Nothing else in the
logic. `__version__` becomes 0.9.1.

Required afterwards:

1. Windows: PR01, PR02, PR15 and PR16 green; 10 of 10 controls caught.
2. Linux and macOS: every battery and every property as before. On POSIX the two functions are
   the same function, so no report may change: for seeds 0–59 and for six public repositories
   (`click`, `requests`, `packaging`, `httpx`, `impress.js`, `lodash`), 0.9.0 and 0.9.1 print the
   same JSON apart from `detector_closure`.
3. A measurement made **on Windows** with 0.9.0 or earlier, on a repository with upper-case
   letters in a path, is to be made again. The study and the benchmark ran on macOS and Linux.
