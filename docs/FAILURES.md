# Where this tool has failed

Every failure found so far, by anyone, with how it was found. Newest first. O10 is the first one
reported from outside.

## Open

| | what | found by | what to do meanwhile |
|---|---|---|---|
| O3 | **No label found outside the listed ecosystems.** The rules still know only the files in `docs/LABELS.md`; recipes for five large projects are there | benchmark | `--version-file`, `--version-regex` |
| O5 | **A refusal for want of a label comes after the whole scan** (68 s on the kernel with 0.10.0) | benchmark | — |
| O9 | `RESULTS.md` is empty: no measurement by anyone else | — | send one |

## Declared as scope (`SCOPE.md`), not as defects

| | what | found by | what to do |
|---|---|---|---|
| O2a | **A wrong file is still believed when one tag agrees by chance** with its first number (a helper crate's `0.1.0` and an old tag `v0.1`) | adversarial ZA04 | `--version-file` in any gate |
| O2b | **Build-number tags (`release-41`) read as versions**: a correct file can be refused, exit 2 | adversarial ZA02 | `--version-file` |
| O2c | **`--at commits` has no tag to check a version file against** | adversarial ZX03 | `--version-file` |
| O10 | **A tag that was never released counts as a publication point.** `astral-sh/ruff` `v0.0.268` was tagged before the version bump and never published; the collision it makes names no second artefact | a participant in [ruff discussion 29122](https://github.com/astral-sh/ruff/discussions/29122), 2026-10-06 — the first failure reported from outside; the same shape in `openai-python` ([discussion 4031](https://github.com/openai/openai-python/discussions/4031)): the published `0.26.5` was built from the commit after the tag | `--tags` to the tags that are releases |
| O7 | Labels are compared as text (`1.0` ≠ `1.0.0`); a mode-only change is not seen; a submodule's content is not read | declared since 0.9.0 | `SCOPE.md`, with what to do for each |

## Fixed

| release | what failed | found by |
|---|---|---|
| 1.0.0 | **file-name exclusions also matched folders**: `**/*_test.*` left out everything under `src/x_test.d/` (O6) | writing the oracle's specification |
| 1.0.0 | no test asserted that `setup.py` is never run (O8); proof SP01, with a positive control | writing the threat model |
| 1.0.0 | the first form of components and file-name exclusions: a component measured under an invalid range; `--at commits` accepted with components; a key repeated in `.closure-drift.json` silently dropped (once giving `clean` over a component in drift); component names cut in the text report; a submodule excluded by its name | adversarial extension 4, before release |
| 1.0.0 | the benchmark reported the largest single process as the memory of the run | the review of the whole repository |
| 0.10.0 | **`clean`, exit 0, over a tiny share of the tags** (`Azure/azure-sdk-for-python`: 9 of 5,508). `clean` now needs at least as many tags compared as not | benchmark, run 1 |
| 0.10.0 | **a wrong version file believed** (`git/git`: a helper crate's `Cargo.toml`; `DefinitelyTyped`: a private `package.json`). A file no tag agrees with decides nothing; a private `package.json` is not read | benchmark, run 1 |
| 0.10.0 | **a version spread over several lines could not be read** (Linux, Node, LLVM). Named groups `part1`, `part2`, … are joined | benchmark, run 1 |
| 0.10.0 | **memory grew with history**: every tree and every version file read was kept, and git mapped whole pack files. The first form of the fix missed its target; 0.10.0 published "535 MB" for every tag of the kernel, which was the largest single process — the whole tree was larger. 1.0.0, whole tree: 900 MB, against 6,541 MB for 0.9.1 | benchmark, run 1; adversarial ZM05, ZM06; benchmark run 2 |
| 0.10.0 | the first form of the fix for a wrong version file **hid real drift, and once gave `clean`, exit 0** | adversarial extension 3, before release; rewritten twice (`tests/PREREGISTRATION.md` §10) |
| 0.9.1 | **on Windows, closure globs matched without regard to case**: one commit, two closures, and in generated repositories two verdicts | property suite against the oracle, on the Windows runner; suspected in writing before the run |
| 0.9.1 | `SECURITY.md` printed the checksum of an unreleased build as that of 0.9.0 | reading the page against `DEPOSIT.sha256` |
| 0.9.0 | files with non-ASCII names silently outside the closure; submodule pointers ignored; root-level `tests/`, `docs/`, `*.md` inside it | acceptance proofs written before the fix: 30 of 51 red against 0.7.1 |
| 0.9.0 | undetermined results exited 0; errors could exit 1, the code for drift; tags that could not be compared were skipped in silence | the same |
| 0.9.0 | measuring a repository could run its commands (`core.fsmonitor`, filters, lazy fetch) and rewrote its index | the same; plain git runs the configured command in 4 of the 16 cases, and in none of them under the tool |
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
