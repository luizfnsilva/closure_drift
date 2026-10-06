# Review of the 0.10.0 documents — as delivered, 2026-10-06

A reviewer who did not write them checked each factual sentence against its source, read-only.
Thirteen findings, committed before any correction; what was done is in the last column.

| # | finding | done |
|---|---|---|
| 1 | README "Tests" table still carried the 0.9.1 scores (120 proofs, 26 mutants, 0 loose) | corrected |
| 2 | STUDY.md "Run 3" named the released script for both runs; they were measured with `08ceb754…` and `89b53499…` | the hashes now come from the reports' own stamps |
| 3 | `results.tsv` headers of run 3 printed the hash of the script present when the table was rebuilt | the same |
| 4 | "measured with 0.10.0" for runs measured with an earlier build; the equivalence check was run but recorded nowhere | wording corrected; the check is in `tests/RECORD.md` |
| 5 | changelog listed a git recipe that was withdrawn | corrected |
| 6 | FAILURES O3 said six recipes; there are five | corrected |
| 7 | ROADMAP still listed O1 and O4 as next | rewritten |
| 8 | LABELS.md pointed at BENCHMARK.md (run 1) for recipe results; `recipes.json` kept the git recipe | pointed at READING.md; git recipe removed with a note |
| 9 | release date 2026-10-05 in three files, measurements dated 2026-10-06 | 2026-10-06 |
| 10 | CPython git memory 217 MB in amendment 5 and 198 MB in READING | both stand, they measure two settings; READING says which |
| 11 | "benchmark of 0.9.1" where run 1 used 0.9.0 | corrected |
| 12 | O5 timing, THREAT_MODEL memory line, READING run 1 "open" items were stale | corrected |
| 13 | "most of it was git" attributed on the kernel, measured on CPython; DefinitelyTyped never said `drift` | corrected |
