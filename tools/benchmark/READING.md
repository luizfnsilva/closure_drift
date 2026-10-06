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
   The report prints the two numbers. By the rule in the code `--strict` answers `incomplete` here;
   that run was not part of the protocol and was not made. Without `--strict`, exit 0 is reached on
   0.16 % of the tags.
4. **`googleapis/google-cloud-python`: refusal at 400 tags, `drift` at every tag** (311 of 6,559
   compared). Both are answers about a monorepo read without `--tags`; neither says anything
   about a package in it.
5. **`DefinitelyTyped`: one tag.** `--would-tag` says `would_drift` on the root `package.json`
   version `0.0.3`, which nobody releases.

Items 2, 3 and 5 are exit codes a gate would act on. They are in `docs/FAILURES.md` as open. (Fixed in 0.10.0: see Run 2 below.)

## What this does not show

One platform, one run, ten repositories chosen by the author. No file system other than the
runner's. No repository beyond 190,000 files. Nothing about Windows at this size.

## Run 2 — 0.10.0, written 2026-10-06 after the results

Protocol: `PREREGISTRATION.md`, "Run 2". Results as produced: `run2/` (CI run 37393129869, script
`08ceb754…`) and `run2b/` (CI run 37405325277, the released script `91ecd5d1…`, for the three
repositories whose recipes were wrong and to measure memory again). B3 of 0.9.1 ran on the same
clone each time.

| repository | B3, 0.9.1 | B3, 0.10.0 | B4, 0.10.0 |
|---|---|---|---|
| `torvalds/linux` | refusal · 96 s · 3285 MB | refusal · 132 s · 535 MB | no_label_at_head · 129 s · 536 MB |
| `llvm/llvm-project` | refusal · 51 s · 1342 MB | refusal · 68 s · 373 MB | no_label_at_head · 68 s · 373 MB |
| `rust-lang/rust` | refusal · 9 s · 656 MB | refusal · 9 s · 606 MB | no_label_at_head · 9 s · 606 MB |
| `python/cpython` | refusal · 9 s · 547 MB | refusal · 9 s · 547 MB | no_label_at_head · 9 s · 548 MB |
| `nodejs/node` | refusal · 39 s · 1048 MB | refusal · 48 s · 173 MB | no_label_at_head · 48 s · 173 MB |
| `kubernetes/kubernetes` | refusal · 50 s · 781 MB | refusal · 50 s · 781 MB | no_label_at_head · 52 s · 781 MB |
| `git/git` | drift · 6 s · 351 MB | incomplete · 6 s · 241 MB | no_label_at_head · 6 s · 242 MB |
| `Azure/azure-sdk-for-python` | clean · 561 s · 771 MB | incomplete · 588 s · 590 MB | no_label_at_head · 574 s · 590 MB |
| `googleapis/google-cloud-python` | drift · 457 s · 580 MB | drift · 476 s · 580 MB | no_label_at_head · 489 s · 580 MB |
| `DefinitelyTyped/DefinitelyTyped` | inconclusive · 2 s · 100 MB | refusal · 2 s · 100 MB | no_label_at_head · 3 s · 100 MB |

| repository | B8, declared version file, every tag |
|---|---|
| `torvalds/linux` | clean, 947 of 947 compared, 0 labels in drift |
| `llvm/llvm-project` | drift, 59 of 327 compared, 5 labels in drift |
| `rust-lang/rust` | incomplete, 74 of 164 compared, 0 labels in drift |
| `python/cpython` | drift, 646 of 674 compared, 2 labels in drift |
| `nodejs/node` | drift, 910 of 962 compared, 8 labels in drift |
| `git/git` | drift, 917 of 1011 compared, 39 labels in drift |

Rows for `linux`, `llvm` and `node` are from `run2b/`; the others from `run2/`, measured before
amendment 5 bounded git's pack mapping and lowered the tree cache, so their memory is higher than
the released script's. On CPython, measured on the author's machine, amendment 5 took the detector
from 277 to 114 MB and its git process from 375 to 198 MB, with the same report (the git
limit alone, measured for amendment 5 with the earlier cache bound: 375 to 217 MB).

What it shows:

- **Memory.** The first form of the fix missed the pre-registered target (the kernel still took
  3.3 GB); the second meets it: 535 MB, 1.38 times the time of 0.9.1 on the same clone.
- **The three wrong answers of run 1 are gone.** `git/git` and the Azure SDK are `incomplete`,
  `DefinitelyTyped` is refused (its only `package.json` is private).
- **Recipes.** With a declared version file the kernel is `clean` over all 947 tags. In LLVM and
  Node the `drift` comes from release candidates: `19.1.0-rc1` … `19.1.0` share `19.1.0` in the file,
  the suffix sits elsewhere, and the recipe does not read it — a limit of the recipe, not a finding
  about either project. CPython: 2 labels in drift on two odd tags (`v2.2`, 2002; `3.2`, 2017).
  The `git/git` recipe read `DEF_VER`, which is not git's version, and is withdrawn
  (`docs/LABELS.md`); its 39 "labels in drift" are not findings.
- F5 at two pairs, as in run 1: the harness compares the ids of two empty closures.

## Run 3 — 1.0.0, written 2026-10-06 after the results

CI run 37506076749, script `74309fe6…`, B3 of 0.9.1 on the same clone. Memory is now the
**whole process tree** (the detector and its `git cat-file`), sampled every 50 ms
(`tests/PREREGISTRATION.md`, amendment to §15); runs 1 and 2 recorded the largest single process.

| repository | every tag, 0.9.1 | every tag, 1.0.0 | with the recipe, 1.0.0 | objects read (recipe) |
|---|---|---|---|---|
| `torvalds/linux` | refusal · 100 s · 6542 MB | refusal · 150 s · 900 MB | clean · 240 s · 900 MB | 368,458 |
| `llvm/llvm-project` | refusal · 52 s · 2693 MB | refusal · 77 s · 614 MB | drift · 73 s · 615 MB | 147,313 |
| `rust-lang/rust` | refusal · 14 s · 1264 MB | refusal · 20 s · 376 MB | incomplete · 18 s · 372 MB | 82,089 |
| `python/cpython` | refusal · 14 s · 874 MB | refusal · 16 s · 248 MB | drift · 55 s · 255 MB | 37,630 |
| `nodejs/node` | refusal · 48 s · 1858 MB | refusal · 62 s · 313 MB | drift · 123 s · 333 MB | 106,255 |
| `kubernetes/kubernetes` | refusal · 54 s · 1281 MB | refusal · 66 s · 266 MB | — | — |
| `git/git` | drift · 6 s · 555 MB | incomplete · 7 s · 206 MB | — | — |
| `Azure/azure-sdk-for-python` | clean · 572 s · 1362 MB | incomplete · 678 s · 317 MB | — | — |
| `googleapis/google-cloud-python` | drift · 451 s · 1088 MB | drift · 543 s · 282 MB | — | — |
| `DefinitelyTyped/DefinitelyTyped` | inconclusive · 2 s · 165 MB | refusal · 2 s · 128 MB | — | — |

- **R6 is met**: no run past its limit, no crash; every tag of the kernel with the recipe in
  900 MB for the whole tree, under the 1 GB of §11, with little room. 0.9.1 on the same clone:
  6,541 MB.
- **The 535 MB published for 0.10.0 was the largest single process**, not the tree; the tree was
  larger. Recorded in `docs/FAILURES.md`.
- Time is not bounded: every tag of the kernel takes 240 s with the recipe.
- Recipes as in run 2: the kernel `clean` over 947 of 947 tags; LLVM and Node `drift` on release
  candidates whose suffix the recipe does not read; CPython 2 labels on two old tags; Rust
  `incomplete`, 74 of 164 compared.
