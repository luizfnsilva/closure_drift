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

`closure_drift.py` was byte-identical across 0.3.0–0.6.0
(sha256 `da5da3c0e781b67b9b3a55800d599c243edc8df649fc90b24a88e289533805c5`), changed in 0.7.0
(`6d8906ef374b73e6b8c58adba813c77c4ff352f5c9c280aa43ff2baa4f804451`, a refusal and not a
measurement), and **changes again in 0.8.0**: it is now
`1125e51615efc3698f09e7bce92bc8647eb468db5471ca79b8ee202cef684cda`.

0.8.0 is the first change that can alter a measurement, and it is stated here rather than left to
be discovered. The 16-hex closure is computed by the same formula as before, and over the seven
public repositories of the README's reference table 0.7.1 and 0.8.0 give identical verdict fields.
Three kinds of repository can get a different answer, and in each the earlier one was wrong: a
closure holding a path that is not plain ASCII, a closure holding a submodule pointer, and two file
lists the earlier formula hashed to the same bytes. The exit code of an undetermined result changed
from `0` to `2`. Each report carries the `detector_closure` of the detector that produced it, which
is how a reader tells them apart. The CHANGELOG records each item with the measurement that showed
it, because a measurement whose instrument moved without saying so is the phenomenon this tool
exists to detect.
