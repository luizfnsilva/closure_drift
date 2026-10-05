# Where this tool has failed

Every failure found so far, by anyone, with how it was found. Newest first. Nobody outside the
author has reported one yet; when someone does, it goes here with their name if they want it.

## Open

| | what | found by | what to do meanwhile |
|---|---|---|---|
| O1 | **`clean`, exit 0, over a tiny share of the tags.** `Azure/azure-sdk-for-python`: 9 of 5,508 compared. The counts are printed; the exit code does not carry them | benchmark, 2026-10-05 | `--strict` in any gate |
| O2 | **A wrong version source is believed.** `git/git`: `drift` on `0.1.0` from a helper crate's `Cargo.toml`. `DefinitelyTyped`: `would_drift` on a root `package.json` nobody releases | benchmark | `--version-file` in any gate |
| O3 | **No label found outside the listed ecosystems.** 6 of 10 large repositories; 8 of the 100 PyPI projects still undecided | benchmark; study run 2 | `--version-file`, `--version-regex` |
| O4 | **Memory grows with history.** 3.4 GB for every tag of the Linux kernel; no limit, no warning | benchmark | fewer tags (`--max-commits`, `--tags`) |
| O5 | **A refusal for want of a label comes after the whole scan** (52 s on the kernel) | benchmark | — |
| O6 | **Exclusions match folders, not only files.** `**/*_test.*` leaves out everything under a folder named `x_test.d`; `**/*.test.*` the same. Glob matching is `fnmatch` on the whole path and is not specified anywhere but `tests/ORACLE_SPEC.md` | writing the oracle's specification | `--closure` cannot bring them back; rename, or accept |
| O7 | Labels are compared as text (`1.0` ≠ `1.0.0`); a mode-only change is not seen; a submodule's content is not read | declared since 0.9.0 | `SCOPE.md` |
| O8 | `setup.py` is never run by construction, and no test asserts it | writing the threat model | — |
| O9 | `RESULTS.md` is empty: no measurement by anyone else | — | send one |

## Fixed

| release | what failed | found by |
|---|---|---|
| 0.9.1 | **on Windows, closure globs matched without regard to case**: one commit, two closures, and in generated repositories two verdicts | property suite against the oracle, on the Windows runner; suspected in writing before the run |
| 0.9.1 | `SECURITY.md` printed the checksum of an unreleased build as that of 0.9.0 | reading the page against `DEPOSIT.sha256` |
| 0.9.0 | files with non-ASCII names silently outside the closure; submodule pointers ignored; root-level `tests/`, `docs/`, `*.md` inside it | acceptance proofs written before the fix: 30 of 51 red against 0.7.1 |
| 0.9.0 | undetermined results exited 0; errors could exit 1, the code for drift; tags that could not be compared were skipped in silence | the same |
| 0.9.0 | measuring a repository could run its commands (`core.fsmonitor`, filters, lazy fetch) and rewrote its index | the same, each with a positive control |
| 0.9.0 | a replace ref hid drift; `GIT_DIR` redirected the measurement; a version pattern could hang the run | first adversarial pass, by a reviewer who did not write the fixes |
| 0.9.0 | two different file lists with one closure id | adversarial pass (HC02), proof U02 |
| 0.9.0 | label read from one file chosen at HEAD: `click` compared at 11 of 71 tags, `requests` at 12 of 162, both reported `clean` and both in drift | study run 1: 34 of 100 without a label, 7 of 21 `drift` read from a constant |
| 0.9.0 | the new label resolution: hangs, order-dependent answers, wrong source, false drift, a vendored package read as the project | third adversarial pass: 41 of 72 cases loose; the resolution was rewritten |
| 0.7.1 | the 0.7.0 tag carried `CITATION.cff` at 0.6.0 with CI green — a version label naming two states, in this repository; the deposited fixture could not run in the deposit | reading the nine files by hand before upload; now `tools/conferir_versao.py` |
| 0.4.0 | the author's working copy had drifted behind the deposited version under the same file name; a run was discarded | preparing an extended run |
| 0.3.0 | 0.1 measured at every commit and overstated drift for anything published at tags | the author, before the first deposit |

Detail for each: `CHANGELOG.md`.

## Failures of the tests

A test that is wrong hides a failure or invents one. These were wrong:

| when | what | found by |
|---|---|---|
| 2026-10-05 | property generator: `core.ignorecase` folded `Lib/` into `lib/` on macOS; the suite would have tested different repositories per platform | PR06, first run |
| 2026-10-05 | a property that could not be evaluated counted as a control caught; a control ran no property at all; PR16 could not fail when `--strict` was ignored | reading the first control table |
| 2026-10-05 | benchmark harness compared closure ids where both closures are empty (F5 at two pairs) | reading the result |
| 2026-10-04 | campaign compared output byte for byte; Windows writes `\r\n` (2 cases loose there) | first CI run on Windows |
| 2026-10-04 | 16 command-execution cases did not run on Windows; a long-path case reported a pass without the file being committed | reading the Windows log |
| 2026-10-04 | after a refactor two mutation controls no longer tested what they named (one did not apply, one passed for another reason) | re-running the controls |

Records: `tests/RECORD.md`, `tests/PROPERTIES_RECORD.md`, `tools/benchmark/READING.md`.
