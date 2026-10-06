# Review of the 1.0.0 candidate — the whole repository, as delivered, 2026-10-06

A reviewer who did not write it was asked one question: which statements can you not sustain?
Read-only, on branch `one-zero` at `f06019d`. Thirty-four findings, committed before any was
corrected; what was done is in the last column.

| # | finding | done |
|---|---|---|
| 1 | the benchmark read the peak of the largest single process (`ru_maxrss`), not of the process tree the protocol names; "535 MB" and the 1 GB target were not measured as written | the harness samples the whole tree; measured again (run 3) |
| 2 | README "Tests" table still 0.10.0's | refilled from the 1.0.0 record |
| 3 | README "Version" still 0.10.0 | rewritten |
| 4 | `DEPOSIT.sha256` and the report examples were 0.10.0's; `reproduce.sh` stopped at its first step | regenerated |
| 5 | `reproduce.sh --study` called the study runner without a work directory | fixed |
| 6 | `docs/CI.md` installed `closure-drift` from PyPI, where it is not published | installs from the release |
| 7 | O7 (labels compared as text, mode-only changes, submodule content) open, not declared with a way to avoid it | declared in `SCOPE.md` with what to do |
| 8 | "flags override the file" is false with components; a gate in a monorepo needs `--component` | `README`, `THREAT_MODEL`, the action and the hook say so; the action takes `component` |
| 9 | the components report carried no `stamp` / `detector_closure` | added |
| 10 | `docs/REPORT.md` said K02 checks every report; it does not check the components report | reworded, CM01–CM10 named |
| 11 | no benchmark run 3 in the repository | run 3 measured and recorded |
| 12 | no recorded run of the 1.0 suites | recorded in `tests/RECORD.md` |
| 13 | the oracle's 1.0 amendments not recorded as its author's | recorded in `tests/PROPERTIES_RECORD.md` |
| 14 | the corpus checked on a build that differs from the release in `__version__` | checked again on the release script |
| 15 | README's seven-repository table: lodash, polars, impress.js figures in no file | replaced by six repositories measured with 1.0.0, results in `tools/reference/` |
| 16 | `docs/WHY.md`: figures from the author's private system with no source; stale cross-references | each figure points to the working paper section that measured it; references fixed |
| 17 | ROADMAP listed shipped items | rewritten |
| 18 | THREAT_MODEL said no case asserts `setup.py` is never run; SP01 does | fixed |
| 19 | FAILURES lacked the five failures extension 4 found | added |
| 20 | `{"components": {}}` refused as "must be a non-empty string" | the message says object |
| 21 | SECURITY implied plain git runs every blocked command | 4 of 16, said so |
| 22 | RESULTS and SECURITY understated which paths a report holds | corrected |
| 23 | "CI enforces this on every push" | on pushes to `main`, tags and pull requests |
| 24 | CONTRIBUTING's "run all of it" omitted properties and the oracle | points to `reproduce.sh` |
| 25 | the exclusion list differed between README and SCOPE, and both were incomplete | one list, complete |
| 26 | README's exit-2 verdict list was incomplete | points to `docs/REPORT.md` |
| 27 | "the 100 most-downloaded PyPI projects" omitted "with a public repository" | fixed |
| 28 | "No input produces a traceback" is universal | "no input we tried" |
| 29 | `objects_read` is in the JSON report only | said so |
| 30 | R5 named proofs CP*; they are CM* | corrected by note |
| 31 | `Development Status :: 4 - Beta` for 1.0.0 | 5 - Production/Stable, with what is stable defined in `SCOPE.md` |
| 32 | stale comments in workflows and `reproduce.sh` | fixed |
| 33 | no 1.0.0 row in SCOPE / SECURITY; SCOPE did not say a 1.0.0 result can differ | added |
| 34 | no review of the whole repository committed | this file |
