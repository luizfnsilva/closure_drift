# Changelog — closure_drift

All notable changes to this deposit. Each deposited version has its own DOI under the concept
DOI 10.5281/zenodo.21763931; cite the version DOI when reporting a measurement.

## 0.5.0 — 2026-09-03

**The measurement script does not change, again.** `closure_drift.py` is byte-identical to 0.3.0 and
0.4.0 (sha256 `da5da3c0e781b67b9b3a55800d599c243edc8df649fc90b24a88e289533805c5`). Every result from
either earlier deposit remains valid and comparable. What changes is, once more, what the deposit
says about itself — and this time what it asks for.

### Added
- `RESULTS.md` — a table for measurements produced by **someone other than the author**, on
  repositories the author does not control. It is **published empty**, and the emptiness is the
  point: as of this release nobody outside the author has run this tool and reported a result.
  Leaving the section out would let a reader assume otherwise. The file states what a line must
  carry to count — version DOI, the `stamp` block, the publication-point setting — and says
  explicitly that results **contradicting** the tool are as welcome as results confirming it, and
  are marked in the table rather than dropped.
- `SCOPE.md` — what this tool does and, in full, **what it will not be extended to do**. The
  (A) well-formed record / (B) reproducible artefact distinction, already in the README, is
  restated here as a commitment rather than a caveat: anything on the (B) side is outside this tool
  by design and will not arrive as a silent extension of it.
- `NOTICE` — the scope of the release, and a plain statement that the author has patent
  applications pending. It **adds no condition**: use requires nothing beyond the Apache License,
  Version 2.0, and the file exists so that anyone evaluating this software knows the surrounding
  situation instead of reconstructing it later. It also states what the licence already says and is
  routinely misread: commercial use carries **no royalty and no payment obligation**.
- README **Reproducibility needs an unambiguous address first** — the argument that label drift is
  not a reproducibility failure but sits upstream of one: *"rebuild version 1.4.2"* presupposes that
  the label names a source, and when it covers more than one code state it names a set. Drift does
  not make the reproducibility question fail; it makes it **unaskable**, in a shape that looks
  exactly like it was asked and answered.
- README **What this is not, and what it does not compete with** — addressing, rebuilding and
  attestation are three different questions, and this tool is only the first. It never rebuilds and
  it issues no attestation. Stated with the disarming case included: if your labels are clean at
  your publication points, this tool has nothing further to offer you, and the right next step is
  the rebuild and attestation tooling rather than this.
- README: an opening that leads with the measured result — `lodash` 69 labels in drift of 78,
  `polars` 40 of 51 — because a reader deciding whether to spend a command deserves the finding
  before the mechanism; and a **Send a result** section with the one-command ask and what the
  sender gets for it.

### Unchanged
- `closure_drift.py`, `tests/fixture_label_only.py`, `LICENSE`, and every reference result. No
  measurement in this deposit was re-run for 0.5.0, and none needed to be.

## 0.4.0 — (date set at deposit)

**The measurement script does not change.** `closure_drift.py` in this deposit is byte-identical
to the one deposited as 0.3.0 (sha256
`da5da3c0e781b67b9b3a55800d599c243edc8df649fc90b24a88e289533805c5`, md5
`a911b025b94df6e77b7c6425a9ce63e6`). Every 0.3.0 result remains valid and reproducible with either
deposit. What changes is what the deposit says about itself.

### Added
- `tests/fixture_label_only.py` — negative fixture. A production ledger of ours (4,756 records,
  26 years of editions, one hand-maintained catalogue label, zero recorded closures) is exactly
  the shape this tool exists to flag: replay of the originating code states is impossible from
  the record alone. The fixture builds that shape synthetically and asserts the tool refuses to
  answer at the default (no tags → exit 2, never a false `clean`) and reports drift — one label,
  N closures — under `--at commits`. A detector that stays quiet here is broken.
- README section **What it does not attest**: the tool checks that addresses are well-formed
  (label present, closure computable, unambiguous) — it never re-executes recorded code states
  and therefore never attests that a published artefact can be re-produced. `clean` is a claim
  about addressing, not about replay.
- README reference results for three further repositories (`impress/impress.js`,
  `lodash/lodash`, `pola-rs/polars`), selected by a rule fixed before the run, measured
  2026-08-23 at the default (tags): drift in all three, by two mechanisms the README now
  distinguishes — release tagged without bumping the version file, and label collision across
  tag families (variant builds / monorepo release schemes reusing one label).
- This changelog.

### Incident, recorded because it is the subject matter
While preparing an extended run after 0.3.0 was deposited, the working copy of this tool used to
drive the run had silently drifted behind the version deposited under its own DOI — same
filename, older per-commit semantics (sha256 of the stale copy:
`fa06f636ebcf548293cb2a3c84484467e9afb4df49949794b2c92e5454911b52`). The instrument exhibited the
phenomenon it measures: one name, two code states, and the only thing recorded was the name. The
run was discarded; the re-run used the deposited bytes, downloaded from the record and
checksum-verified against the Zenodo file entry before execution, with the verifying gate kept in
the run script. The verdicts above are from that re-run. If you script this tool, pin the version
DOI and verify the checksum — the report's `detector_closure` stamp exists so that this failure
is at least detectable after the fact.

## 0.3.0 — 2026-08-02 (doi:10.5281/zenodo.21763932)
- Publication-point semantics: evaluate at tags by default, `--at commits` only where publication
  is genuinely continuous. Supersedes 0.1's unconditional per-commit comparison, which reported
  drift on every repository measured, healthy ones included — an alarm that always fires carries
  no information.
- Repository-side configuration file `.closure-drift.json`.
- Self-stamping report: `measured_at_head`, `working_tree_dirty`, `detector_closure`.

## 0.1
- Initial version. Compared label to closure at every commit, unconditionally. Superseded:
  results from 0.1 overstate drift for any repository that publishes at tags.
