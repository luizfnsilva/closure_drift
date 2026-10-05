# Reading the benchmark — written 2026-10-05, after the results

The table is [`BENCHMARK.md`](BENCHMARK.md), generated from `results/`. This page is what the
author takes from it. It is a reading, made after seeing the numbers.

## Scale

- **Nothing timed out.** The slowest run is every tag of `Azure/azure-sdk-for-python`
  (5,508 tags): 543 s.
- **Memory is the limit that will be met first.** Every tag of `torvalds/linux`: 3.4 GB; the
  default 400 tags: 2.7 GB. Every tree object read is kept for the whole run. A runner with 2 GB
  would not finish the kernel. Nothing was killed here (16 GB).
- **A refusal for want of a label costs a full scan.** The kernel run spends 52 s and 2.7 GB
  before it says it found no version label.
- B1 and B2 printed the same bytes in 10 of 10.

## The oracle at scale

18 comparisons (two pairs in each of nine repositories; `DefinitelyTyped` has one tag), up to
40,577 files in a closure. Ids, counts and path lists agree in every one
where both sides have files.

**F5 at two pairs (`llvm`, `git`) is the harness, not a difference.** The older tag has no file in
the default closure: the detector reports no id for an empty closure, the oracle reports the hash
of empty input, and the harness compared the two fields without looking at the count, which is 0
on both sides. The property suite already skips that comparison; the benchmark harness did not.
The result files are kept as produced.

## The answers — where the defaults fail

1. **Six of ten: no version label found** (`linux`, `llvm`, `rust`, `cpython`, `node`,
   `kubernetes`). The rules know Python build files, `Cargo.toml`, `package.json` and a few
   others at the root. A version kept in a `Makefile`, a C header or a Go file is not found.
   Outside the ecosystems listed in `docs/LABELS.md`, pass `--version-file` and `--version-regex`.
2. **`git/git`: `drift`, exit 1, and it is not git's version that drifts.** The label read is
   `0.1.0` from the root `Cargo.toml`, a helper crate added in 2025; git's version comes from
   `GIT-VERSION-GEN`. 20 of 1,011 tags were compared. A single wrong source is believed.
3. **`Azure/azure-sdk-for-python`, every tag: `clean`, exit 0, with 9 of 5,508 tags compared.**
   The report prints the two numbers and `--strict` answers `incomplete`; without `--strict`, exit
   0 is reached on 0.16 % of the tags.
4. **`googleapis/google-cloud-python`: refusal at 400 tags, `drift` at every tag** (311 of 6,559
   compared). Both are answers about a monorepo read without `--tags`; neither says anything
   about a package in it.
5. **`DefinitelyTyped`: one tag.** `--would-tag` says `would_drift` on the root `package.json`
   version `0.0.3`, which nobody releases.

Items 2, 3 and 5 are exit codes a gate would act on. They are in `docs/FAILURES.md` as open.

## What this does not show

One platform, one run, ten repositories chosen by the author. No file system other than the
runner's. No repository beyond 190,000 files. Nothing about Windows at this size.
