# Threat model

What this tool assumes, what it defends, and what it does not. Each defence names its test; a
line without a test says so.

## Assets

| | |
|---|---|
| A1 | the machine that runs the tool: nothing from the measured repository may execute on it |
| A2 | the measured repository: never written to |
| A3 | the answer: `clean` (exit 0) must not be obtainable by an input that hides drift |
| A4 | the reader of the output: a terminal or a CI log must not be made to show a forged verdict |

## Trust

Trusted: the `git` binary on `PATH`, the Python interpreter, the copy of `closure_drift.py` you run
(verify it: `SECURITY.md`), your own command line.

Not trusted: every byte of the measured repository — objects, refs, tag names, file names, file
contents, its `.git/config`, its `.closure-drift.json` — and eleven git variables that would
redirect the measurement if set in your environment (`GIT_DIR`, `GIT_WORK_TREE` and kin).

## Attackers

| | who | wants |
|---|---|---|
| T1 | the author of a repository you measure | to run a command on your machine (A1) |
| T2 | the same | a `clean` over history that holds drift (A3) |
| T3 | the same | to hang or crash your pipeline, or have a crash read as a pass |
| T4 | the same | to forge lines in your log (A4) |
| T5 | a contributor to your own repository | to pass a `--would-tag` gate while reusing a label |

## Defences, and where each is tested

| threat | defence | test |
|---|---|---|
| T1 `core.fsmonitor`, filters, lazy fetch | fixed git options on every call; `git status` skipped where a filter is configured; partial clones refused on git older than 2.45 | adversarial CX series, 16 cases. Each carries a positive control; plain git runs the configured command in 4 of them on the machines tested, and in none of those under the tool |
| T2 replace refs; `GIT_DIR` and ten other redirecting variables | `--no-replace-objects`; the variables are removed | adversarial AF01, EC10 |
| T1, T3 a version pattern in the repository's config | matched in a child process under a time limit | adversarial EC18 and LD series |
| T1 `setup.py` | parsed with `ast`, never imported or run | **no dedicated case**: by construction only |
| T2 non-ASCII, quoted or invalid file names | paths are read from tree objects, never from quoted output | battery C01–C06; properties PR01, PR02 against the oracle |
| T2 two file lists with one 16-hex id | identity is the full SHA-256 (`closure_ids`) | adversarial HC series; battery U02 |
| T2 two files declaring different versions | counted, and never reported `clean` | adversarial LS and LC series |
| T2 a tag list arranged so that order hides a collision | every closure of a label is kept, whatever the order | properties PR08, PR09, PR11 |
| T3 malformed trees, broken config, very large or deep input | named refusal, exit 2; exit 0 is `clean` only; no traceback | battery D series; adversarial EC and TR series; property PR13 over every run of the suite |
| T4 control characters, line breaks, bidirectional marks in labels, paths, tag names | escaped on output | adversarial OI series |
| T5 a label already used by an old tag outside the scan window | `--would-tag` reads every tag | battery W series; adversarial WT series; property PR12 |

## Not defended

- **A git binary that lies**, or a malicious Python. Out of scope.
- **Your own environment beyond the eleven variables.** `GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS`,
  `GIT_CONFIG_GLOBAL`, `GIT_EXEC_PATH` and your global git config are obeyed. Not tested.
- **SHA-1 collisions in git objects.** The closure is as strong as git's object ids and no stronger.
- **Code that determines your output and sits outside the closure globs**, under an excluded
  folder, or in a submodule's content (only the pointer is read). `clean` says nothing about it.
- **Mode-only changes.** A file made executable keeps its object id (property PR07 tests the limit).
- **Labels that differ as text and are one version** (`1.0`, `1.0.0`).
- **The label heuristics.** Without `--version-file` the label is found by rules (`docs/LABELS.md`);
  a repository can be arranged so that they read the wrong file. With two disagreeing sources the
  verdict is never `clean`, but a single wrong source is believed. Pin `--version-file` in a gate.
- **A `.closure-drift.json` committed by the attacker in a repository you gate.** It can narrow the
  closure or the tags. Review it like code, or pass the flags on the command line; flags override it.
- **Resource exhaustion by size.** There is no memory limit; see `tools/benchmark/BENCHMARK.md`.
- **Git versions and file systems not in `tests/RECORD.md`.**

## What a pass of the tests means

The cases executed behaved as written, on the platforms listed. It is not a proof. The reviewers so far
worked at the author's request; nobody outside this project has attacked the tool yet. `docs/FAILURES.md` lists what was found so far.
