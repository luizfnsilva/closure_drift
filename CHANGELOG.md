# Changelog — closure_drift

All notable changes to this deposit. Each deposited version has its own DOI under the concept
DOI 10.5281/zenodo.21763931; cite the version DOI when reporting a measurement.

## 0.6.0 — 2026-09-05

**The measurement script does not change, a third time.** `closure_drift.py` is byte-identical to
0.3.0, 0.4.0 and 0.5.0 (sha256 `da5da3c0e781b67b9b3a55800d599c243edc8df649fc90b24a88e289533805c5`).
**Every result produced under any of those deposits remains valid and comparable**, and nothing in
this release requires a re-run. What changes is the licence file, which was wrong, and where this
software can now be found.

### Fixed
- **`LICENSE` now carries the unabridged text of the Apache License, Version 2.0.** The file
  deposited as 0.3.0, 0.4.0 and 0.5.0 was an **abridged** version of that licence: 1,064 words
  against the 1,581 of the text published at `apache.org/licenses/LICENSE-2.0.txt`. Section 2
  (copyright grant), **section 3 (patent grant)** and section 6 (trademarks) were word-for-word
  identical. Section 1 (definitions, 467 → 346 words), section 4 (redistribution, 325 → 137),
  section 5, section 7 (disclaimer of warranty, 84 → 57), section 8 (limitation of liability,
  114 → 76) and section 9 were shortened, and the appendix was absent.

  Two consequences, and neither was intended. Automated licence detection could not identify the
  file, so a repository carrying it is reported as having no asserted licence — which is the correct
  reading of a modified text, not a tooling defect. And the shortened clauses included **section 7
  and section 8, the two that protect the author**, and section 4's requirement that a `NOTICE` file
  be carried into redistributions — the very file this deposit ships in order to have it carried.

  The file is now byte-identical to the text published at
  `apache.org/licenses/LICENSE-2.0.txt` (sha256
  `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`), appendix included and
  placeholders left as the canonical text leaves them. The copyright attribution sits in `NOTICE`,
  which is the file the licence provides for it.

  The licence **named** in every deposit has always been Apache-2.0: `README.md`, `NOTICE`,
  `CITATION.cff` and the Zenodo record metadata all say so, and the grant sections a licensee relies
  on were already identical to the canonical text. From this deposit onwards the file says it too.
  Anyone who took the earlier deposits under the Apache License, Version 2.0 was taking them under
  the licence that was named, and the corrected text is the one to rely on.

  *Recorded at this length because it is the subject matter.* This project's claim is that a record
  can look well-formed and not be, and that the system holding it cannot notice, because the label is
  the only thing it recorded. A file called `LICENSE`, under metadata reading `apache2.0`, in three
  deposits with DOIs, whose text was not that licence, is that failure in this project's own record —
  the second such instance, after the working-copy drift recorded under 0.4.0.

### Added
- **A public source repository**: <https://github.com/luizfnsilva/closure_drift>. It was private
  until this release, which is why `RESULTS.md` could only ask for results by email and why the
  threat model in the related article recorded "a reader cannot verify without trusting" as an
  unmet condition. It can now be verified without trusting.
- **Measurements can be reported through an issue form**, and so can the more valuable case — that
  the tool is **wrong** about a repository. Email remains available for results that should not be
  public. `RESULTS.md` carries both channels.
- **A deposit gate.** The repository records the sha256 of each file of this deposit and checks them
  on every push, offline against a manifest or by re-fetching the record. If the repository and the
  deposit ever disagreed, a measurement citing the DOI could not be checked against the code that
  produced it.
- `CITATION.cff` now carries the concept DOI and the repository URL, so the citation offered by
  software that reads it resolves to the deposit instead of naming it in prose.

### Unchanged
- `closure_drift.py`, `tests/fixture_label_only.py`, `SCOPE.md`, `NOTICE`, and every reference
  result. No measurement in this deposit was re-run for 0.6.0, and none needed to be.

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
