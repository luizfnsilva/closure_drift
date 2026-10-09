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

Run it: push a branch named `regression-check/<anything>` (this branch's detector) or
`regression-check-<tag>/<anything>` (that tag's), then
`python3 tools/regression/regress.py summary <the check-*.json files>`.
