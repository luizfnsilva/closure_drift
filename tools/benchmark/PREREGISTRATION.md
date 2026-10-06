# Pre-registration — large repositories

Written 2026-10-05, before the harness and before any of these repositories was measured with any
version of this tool. Detector: 0.9.0 as deposited, sha256
`6548f891a826034c35ef83b276578c79564b57f892a54422af5c1be44591137c`.

## The question

Where does 0.9.0 stop working as repositories get large: in time, in memory, or in the answer?

This is not a sample and no proportion is drawn from it. The ten were chosen to be hard.

## The ten, and why each

| repository | why |
|---|---|
| `torvalds/linux` | the largest tree in common use; 900+ tags |
| `llvm/llvm-project` | more files than the kernel; a monorepo of projects |
| `rust-lang/rust` | long merge-heavy history |
| `python/cpython` | 30 years of tags; `Lib/` beside the default glob `lib/**` |
| `nodejs/node` | large vendored dependencies inside the tree |
| `kubernetes/kubernetes` | Go monorepo, `vendor/` excluded by default |
| `git/git` | the substrate this tool reads through |
| `Azure/azure-sdk-for-python` | thousands of tags in hundreds of families |
| `googleapis/google-cloud-python` | the same shape, another organisation |
| `DefinitelyTyped/DefinitelyTyped` | very many folders, few or no tags |

Left out and said so: Chromium and the Android tree do not fit on the runner's disk.

No repository is added or removed after a result is seen. A clone that fails is a row.

## The machine

A GitHub-hosted `ubuntu-24.04` runner, one repository per job, full bare clone, deleted after.
Runner, CPU count, memory, git and Python versions are recorded with each result. Times on shared
runners vary; they are reported as measured, once, with no claim of precision.

## The runs, each under a limit of 40 minutes

| id | command |
|---|---|
| B1 | `closure_drift.py CLONE --json` |
| B2 | the same again |
| B3 | `--json --max-commits 1000000` (every tag) |
| B4 | `--would-tag --json` |
| B5 | `--at commits --json` |
| B6 | `--compare OLDEST NEWEST --json`, and `--compare MEDIAN NEWEST --json` — the oldest, median and newest tag by creation date among those that point at a commit |
| B7 | `tests/oracle.py CLONE --compare` on the same two pairs, default closure |

Recorded for each: exit code, wall time, peak resident memory of the process, the first line of
stderr, the sha256 of stdout, and from the report: verdict, labels, points scanned and compared.
For the clone: time, size on disk, tags, commits reachable from HEAD, files at HEAD.

## What counts as a failure

| id | failure |
|---|---|
| F1 | a run does not finish in 40 minutes |
| F2 | a run is killed for memory, or any exit code other than 0, 1, 2 |
| F3 | `Traceback` or `internal error` on stderr |
| F4 | B1 and B2 print different bytes |
| F5 | a closure id or file count in B6 differs from the oracle's in B7 |
| F6 | a path list in B6 differs from the oracle's in B7 |

A verdict of `no_labels`, `inconclusive` or a refusal for want of a version label is not a
failure of scale; it is reported as the answer. Nothing is tuned per repository.

## What will be published, whatever comes out

One row per repository and run, every failure by id, and the raw result files. If a failure is
found, 0.9.0 is not changed for it in this round: it is written in `docs/FAILURES.md` as open.

## Run 2 — added 2026-10-05, before run 2

Run 1 is kept. Run 2: the same ten repositories, the same runs B1–B7, with release 0.10.0, plus

| id | command |
|---|---|
| B3_baseline | B3 with 0.9.1, on the same clone, for time and memory |
| B8 | every tag, with the version file and pattern written in `recipes.json` before this run |

Required (§10 of `tests/PREREGISTRATION.md`): B3 of `torvalds/linux` under 1.5 GB peak; no B3 more
than 1.5 times slower than its B3_baseline; `git/git` B3 not `drift` and B4 not `would_drift`;
`DefinitelyTyped` B4 not `would_drift`; `Azure/azure-sdk-for-python` B3 not `clean`. B8 is reported
as it comes out.
