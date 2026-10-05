# Review of the 0.9.1 documents — as delivered, 2026-10-05

A reviewer who did not write them checked each factual sentence against its source, read-only.
Eighteen findings, committed here before any was corrected. What was done about each is in the
second column, filled in afterwards.

| # | finding | done |
|---|---|---|
| 1 | `READING.md` said 20 comparisons with the oracle; there are 18 (one repository has a single tag) | corrected |
| 2 | README and the deposit description said the oracle agrees "at every pair"; two pairs are recorded as differing (both closures empty, a harness artefact) | "at every pair with files" |
| 3 | README said two answers are wrong; `READING.md` and `FAILURES.md` count three | three |
| 4 | README said the tool starts `git` and nothing else; it also starts itself to match a version pattern | corrected |
| 5 | "16 cases with a positive control (plain git does run the command)": plain git runs it in 4 of the 16 | corrected |
| 6 | the threat model called the git variables of the environment untrusted and the environment "cleaned"; eleven named variables are removed and `GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS`, `GIT_EXEC_PATH` and others are obeyed | moved to *Not defended* |
| 7 | "huge or cyclic input": nothing tests a cycle | "cyclic" removed |
| 8 | PR06 cited for id collisions, which it does not test; AF01 filed under the wrong threat | corrected |
| 9 | "the study was measured on macOS … and says so": its files record no platform | says what is and is not recorded |
| 10 | README table header claimed the same scores under Python 3.9; for 0.9.1 only the battery was run there | header corrected |
| 11 | "nobody outside the author has attacked this tool" beside "a reviewer who did not write the fixes" | reworded |
| 12 | the 0.9.0 changelog entry said two adversarial passes; there were three | corrected in place, noted under 0.9.1 |
| 13 | "each of the 87 labels is a line in `collisions.tsv`": it has one line per tag, 225 | corrected |
| 14 | "every tag of the kernel in 90 s": that run ends in a refusal; 947 of 949 tags point at commits | reworded |
| 15 | "measure again what you measured on Windows" is broader than the changelog's "with upper-case letters in a path" | left broad: a glob with upper case is affected too |
| 16 | `reproduce.sh` said "about ten minutes" with no timing on record | no duration claimed |
| 17 | only one row of the threat model says "no dedicated case" | stands; it is the only one found |
| 18 | "PR06 and PR07 found a case in 41 of 60 seeds, PR12 in 48" is in no file | it is what the suite prints (`41 seeds`, `48 seeds`); left |
