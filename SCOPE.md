# Scope — what this tool does, and what it will not be extended to do

This file exists because a detector that keeps growing until it does everything ends up measuring
nothing, and because anyone deciding whether to depend on this tool deserves to know its edges
before they depend on it rather than after.

## What it does

One question, and nothing else:

> **does a declared version label identify exactly one state of the producing code, at the points
> where this repository publishes?**

It reads a git repository. It computes, at each publication point, the **label** (the version you
declare) and the **closure** (SHA-256 over `(path, git blob id)` for the files that determine your
output), and compares them across history. A label covering more than one closure means artefacts
published under it are ambiguously addressed.

It is read-only, has zero dependencies, needs no network, and never writes to the repository it
measures.

## What it does not do — and will not

These are not gaps waiting to be filled. They are the boundary, and the boundary is the design.

- **It never re-executes anything.** It does not run your build, your tests, or any recorded code
  state. A `clean` verdict says your addresses are unambiguous over the range scanned; it says
  nothing about whether re-running the recorded state reproduces the published output.
- **It attests nothing.** It issues no certificate, no signed statement, no attestation of
  provenance, and no verdict that a third party is meant to rely on as proof. It produces a
  measurement and stamps the state it was measured in.
- **It does not judge your process.** Drift is a property of an addressing scheme, not a defect of
  character. `lodash` and `polars` are in drift by a naming-scheme property, not by an oversight,
  and the README distinguishes the two mechanisms for exactly that reason.
- **It does not decide what determines your output.** The default closure globs are a guess. If
  they are wrong for your project, the number is wrong, and the tool prints what it used so you can
  see that.
- **It does not see a change of file mode alone.** The closure is `(path, object id)`. A file made
  executable, or replaced by a symbolic link holding the same bytes, keeps the same object id.
- **It never looks under the excluded folders.** `test/`, `tests/`, `spec/`, `docs/`, `vendor/`,
  `node_modules/` and `*.md` are outside every closure, even when a `--closure` glob matches them.
  Code that determines your output and lives there can change without this tool noticing.
- **Its closure identifiers are not a defence against someone crafting collisions.** The 16-hex
  value is kept for comparability; identity is decided by a full SHA-256, which is as strong as
  git's own object ids are, and no stronger.
- **It is not a proof of anything.** `clean` means clean over the range scanned, at the points you
  told it about.
- **Without `--version-file`, finding the label is best effort.** The rules read the files a
  build declares and refuse a file that no tag named for a version agrees with. They can still be
  fooled: a helper file that agrees with one old tag by chance is believed; build-number tags
  (`release-41`) can make a correct file look contradicted, which ends at exit 2; `--at commits`
  has no tag to check against. A file given with `--version-file` is never second-guessed. **In a
  gate, pass it.**
- **Three things the closure does not see** (declared since 0.9.0). Labels are compared as written:
  `1.0` and `1.0.0` are two labels, so two tags building the same version under those spellings
  are not compared — write versions one way. A change of file mode alone keeps the object id —
  check modes separately (`git diff --summary A B`). A submodule's content is not read, only its
  pointer — measure the submodule's repository on its own.
- **A publication point is a tag.** Whether a tag was ever released is recorded in a package
  index, not in the repository, and this tool reads only the repository. A tag never released is
  still compared (`astral-sh/ruff` `v0.0.268`). Pass `--tags` to select the tags that are
  releases.

## The distinction that governs all of the above

Two claims that are constantly confused, and keeping them apart is the whole discipline of this
tool:

| | claim | who checks it |
|---|---|---|
| **(A)** | the record is **well-formed** — a label exists, a closure is computable, addresses are unambiguous | **this tool** |
| **(B)** | the published artefact **can be re-produced** — re-executing the recorded state yields the published output | not this tool, and not by inspecting shape |

Reading (A) as (B) is a defect the author paid to learn about in his own system, and the negative
fixture — `fixture_label_only.py`, flat beside the detector in this deposit and in `tests/` in the
source repository — exists so that a detector which stays quiet on that shape fails loudly.

**Anything on the (B) side is outside this tool by design and will remain outside it.** If your
problem lives there, this tool will not grow to meet you — say so and it can be discussed, but it
will not arrive as a silent extension of this one.

## Stability

| versions | script sha256 |
|---|---|
| 0.3.0 – 0.6.0 | `da5da3c0e781b67b9b3a55800d599c243edc8df649fc90b24a88e289533805c5` |
| 0.7.0 – 0.7.1 | `6d8906ef374b73e6b8c58adba813c77c4ff352f5c9c280aa43ff2baa4f804451` |
| 0.9.0 | `6548f891a826034c35ef83b276578c79564b57f892a54422af5c1be44591137c` |
| 0.9.1 | `89b5349928eba22b0394d01940ed3d4aa989d6820f48fdddf189ad521689c51c` |
| 0.10.0 | `91ecd5d1437632b3db65fe606b39b3c924351ac555eb4d5b2704d33785065990` |
| 1.0.0 | `74309fe6db463a53e2dce112596b425a596a1a38dce413054e2db32a23f99f0d` |

0.9.0 is the first change that can alter a measurement: it reads the label at every tag and
compares more of them, so a `clean` from an earlier version can be `drift` now. `CHANGELOG.md`
says what to measure again. 0.9.1 changes a measurement only on Windows, where 0.9.0 matched
closure globs without regard to case. 0.10.0 can turn a `clean` or `drift` of 0.9.x into
`incomplete`. Every report carries the `detector_closure` of the detector that produced it.

1.0.0 can change a result of 0.10.0 where code sits under a folder whose name looks like a test or
a document (`src/x_test.d/`): that code is now in the closure. On the 100 repositories of the
regression corpus, no result changed.

**What 1.0 keeps stable** until 2.0: the command-line options, the exit codes and what each means,
the verdict names, and `report_format: 2` (fields are only added). A change to any of these is a
new major version.
