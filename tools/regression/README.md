# Regression corpus

The 100 repositories of `tools/study/`, each pinned to a recorded HEAD and set of tags
(`corpus/`, recorded by 0.10.0 on 2026-10-06). Protocol: `tests/PREREGISTRATION.md` §12.

| check | detector | result |
|---|---|---|
| `checks/v0.10.0.json` | 0.10.0, the one that recorded it | 100 of 100 match |
| `checks/v0.9.1-control.json` | 0.9.1, the control | 96 match; `idna`, `tqdm`, `scipy`, `coveragepy` differ (`clean` against `incomplete`), as predicted |
| `checks/candidate-892a3e1f.json` | a 1.0 candidate with the file-name exclusion fix | 100 of 100 match, as predicted |
| `checks/v1.0.0-candidate-74309fe6.json` | the 1.0.0 script | 100 of 100 match |
| `checks/v1.1.0-candidate-e2a67a5a.json` | the 1.1.0 script | 100 of 100 match, as predicted (§16) |
| `checks/v1.1.1-candidate-890616f7.json` | the 1.1.1 script | 100 of 100 match, as predicted (§17) |
| `checks/v1.1.2-candidate-a61858aa.json` | the 1.1.2 script | 100 of 100 match, as predicted (§18) |
| `checks/v1.1.3-candidate-101905f6.json` | the 1.1.3 script | 100 of 100 match, as predicted (§19) |
| `checks/v1.2.0-candidate-7dd5833c.json` | the 1.2.0 script | 100 of 100 match, as predicted (§20) |
| `checks/v1.2.1-candidate-0703760a.json` | the 1.2.1 script | 99 of 99 checkable match, as predicted (§21); `apache/arrow` not checkable: its tag `r-universe-release` moved upstream |
| `checks/v1.2.2-candidate-5305234f.json` | the 1.2.2 script | 99 of 99 checkable match (§22); `apache/arrow` not checkable |
| `checks/v1.3.0-candidate-b724d56c.json` | the 1.3.0 script | 99 of 99 checkable match, as predicted (§24); `apache/arrow` not checkable |
| `checks/v1.3.1-candidate-fccba5dd.json` | the 1.3.1 script | 99 of 99 checkable match, as predicted (§25); `apache/arrow` not checkable |
| `checks/v1.3.2-candidate-045362a0.json` | the 1.3.2 script | 99 of 99 checkable match, as predicted (§26); `apache/arrow` not checkable |
| `checks/v1.3.3-candidate-7d4bbe46.json` | the 1.3.3 script | 99 of 99 checkable match, as predicted (§27); `apache/arrow` not checkable |
| `checks/v1.4.0-candidate-8ed98594.json` | the 1.4.0 script | 99 of 99 checkable match, as predicted (§28); the labels in drift split 79 / 7 / 1 by mechanism, as predicted; `apache/arrow` not checkable |
| `checks/v1.5.0-candidate-c0c6ae18.json` | the 1.5.0 script | 99 of 99 checkable match, as predicted (§29); mechanisms 79 / 7 / 1 unchanged; `apache/arrow` not checkable |
| `checks/v1.5.1-candidate-3fafc146.json` | the 1.5.1 script | 99 of 99 checkable match, as predicted (§30); mechanisms 79 / 7 / 1; `apache/arrow` not checkable |
| `checks/v1.6.0-candidate-0e4e5a26.json` | the 1.6.0 script | 99 of 99 checkable match, as predicted (§31); mechanisms 79 / 7 / 1; `apache/arrow` not checkable |
| `checks/v1.7.0-candidate-ec0a7666.json` | the 1.7.0 script | 99 of 99 checkable match, as predicted (§32); mechanisms 79 / 7 / 1; `apache/arrow` not checkable |
| `checks/v1.8.0-candidate-187d0eaa.json` | the 1.8.0 script | 99 of 99 checkable match, as predicted (§34); mechanisms 79 / 7 / 1; `apache/arrow` not checkable |
| `checks/v1.8.1-candidate-e25ad746.json` | the 1.8.1 script (1.8.0 plus the version line) | 99 of 99 checkable match (run 43495698587); mechanisms 79 / 7 / 1; `apache/arrow` not checkable |

Run it: push a branch named `regression-check/<anything>` (this branch's detector) or
`regression-check-<tag>/<anything>` (that tag's), then
`python3 tools/regression/regress.py summary <the check-*.json files>`.
