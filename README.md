# closure_drift

**Does your version label name exactly one version of your code?**

`lodash` publishes 78 labels across 400 tags; 69 of them cover more than one code state. `polars`:
51 labels, 40 in drift, one of them covering 16. Neither project is badly run — both are in drift
by a property of their release scheme, and neither could have noticed from what they recorded.

That is the failure this tool measures. When you publish something and address it by
`(input, version)`, that address is sound only if the version identifies exactly one state of the
producing code. Nothing enforces it — the label is a string a human edits. When two code states
share a label, one address denotes two outputs, and **the system cannot notice, because the label is
the only thing it recorded.**

One command tells you whether it is happening to you. Read-only, zero dependencies, one file, no
network, nothing written to your repository.

```
python3 closure_drift.py                          # your repo, drift at tags
python3 closure_drift.py --at commits             # continuously published output
python3 closure_drift.py --closure 'src/**/*.py'  # say what determines your output
python3 closure_drift.py --json                   # machine-readable
```

Exit code is `1` when a label covers more than one closure at a publication point.

## What it measures

For each **publication point** it computes two things and compares them across the history:

| | |
|---|---|
| **label** | the version you declare, read from your version file |
| **closure** | SHA-256 over `(path, git blob id)` for the files that determine your output |

A label covering more than one closure means artefacts published under it are ambiguously addressed.

## Reproducibility needs an unambiguous address first

The reproducibility question is: **rebuild the source, do you get the same artefact, bit for bit?**

That question presupposes something nobody checks. It presupposes that *"rebuild version 1.4.2"*
**names a source**. If the label `1.4.2` covers more than one state of the producing code, it does
not name a source — it names a *set*, and the rebuild you perform is one draw from that set. You can
then get a mismatch and spend a week hunting a non-determinism that was never in the build at all,
or get a match and have learned less than you think.

So label drift is not a reproducibility failure. It sits **upstream** of one, and it is worse in a
specific way:

> it does not make the reproducibility question fail. It makes it **unaskable** — and unaskable in a
> shape that looks exactly like it was asked and answered.

That is the same failure the rest of this README keeps circling: *the system cannot notice, because
the label is the only thing it recorded.* Two of the three repositories measured on 2026-08-23 are
in drift by a property of their release scheme, not by anyone's oversight. Neither could have
noticed from what it records.

This tool checks that precondition, in one command, and then stops.

## What this is not, and what it does not compete with

Three things are constantly bundled together, and this tool is deliberately only the first:

| | the question | this tool |
|---|---|---|
| **addressing** | does the label name exactly one code state? | **yes, this is all it does** |
| **rebuilding** | does re-executing that state yield the published bits? | **no.** It never runs your code. Rebuild-and-compare tooling answers this, by actually rebuilding |
| **attestation** | is there a signed, verifiable statement about how the artefact was produced, that a third party can rely on? | **no.** It issues no attestation, signs nothing, and asks you to rely on nothing. Supply-chain attestation frameworks exist for this |

The three are complementary, not alternatives — but the first is the one that can quietly invalidate
the other two, because both of them take *"which source?"* as given, and it is not given.

And the disarming case, said plainly: **if your labels are clean at your publication points, this
tool has nothing further to offer you.** It will exit `0`, you will have spent one command, and the
right next step is the rebuild and attestation tooling, not this. A detector that tries to stay
useful after answering its question stops being a detector.

`SCOPE.md` states the boundary in full, including what this tool will not be extended to do.

## What it does not attest

This tool answers one question — *does the label identify exactly one code state at the points
where you publish?* — and nothing else. In particular, keep two claims apart:

- **(A) the record is well-formed**: a version label exists, a closure can be computed, hashes are
  present and comparable. That is the shape this tool checks.
- **(B) the published artefact can be re-produced**: re-executing the recorded code state yields
  the published output. This tool **never runs your code** and therefore never attests (B).

A `clean` verdict means your addresses are unambiguous over the range scanned — it does not mean
your outputs were replayed or verified. Reading (A) as (B) is a defect we paid to learn about in
our own system: a 26-year, 4,756-record production ledger of ours is 100% label-only under a
single catalogue label — every record carries a content hash, none carries its closure — so replay
of the originating code states is impossible from the record alone, a fact no amount of (A)-shape
checking can repair. That corpus is now this tool's negative fixture (see *Tests* below): a
detector that stays quiet on that shape is broken.

## Where your publication points are

This is the setting that matters, and getting it wrong makes the tool useless.

- `--at tags` **(default)** — you publish at releases. Between tags the code moves and the label does
  not, and that is not drift; that is what a release is.
- `--at commits` — you publish continuously: a feed, a dashboard, generated documentation, a daily
  edition, model output served from a rolling checkpoint. Then every commit publishes, and every
  commit is a point.

An earlier version of this tool compared at every commit unconditionally. It reported drift in every
repository it was pointed at, including four healthy ones — because measured that way, every project
on earth is guilty. A detector whose alarm always fires is worth what a test that never fails is
worth. If you are reading the source and wondering why the publication-point logic exists, that is
why.

## Reference results

Measured 2026-08-02 with the 0.3.0 script (byte-identical in this deposit):

| Repository | Points | Labels | Worst label | Verdict |
|---|---|---|---|---|
| `pallets/click` | 68 tags | 10 | 1 closure | clean |
| `psf/requests` | 66 tags | 12 | 1 closure | clean |
| `pypa/packaging` | 17 tags | 13 | 1 closure | clean |
| `encode/httpx` | 28 tags | 28 | 1 closure | clean |
| a system publishing daily | 133 commits | 2 | **6 closures** | **drift** |

Measured 2026-08-23, same script, at the default (tags), on three further repositories selected by
a rule fixed before the run:

| Repository | Points | Labels | In drift | Worst label | Verdict |
|---|---|---|---|---|---|
| `impress/impress.js` | 15 tags | 4 | 2 | 2 closures | **drift** |
| `lodash/lodash` | 400 of 440 tags | 78 | 69 | 4 closures | **drift** |
| `pola-rs/polars` | 400 of 570 tags | 51 | 40 | 16 closures | **drift** |

Two distinct mechanisms produce these, and they should be cited as distinct. In `impress.js` it is
the simple forgetting: a release tagged without bumping the version file (`1.1.0` is declared both
at tag `1.1.0` and at tag `v2.0.0`). In `lodash` and `polars` it is **label collision across tag
families**: variant tags (`-amd`/`-es`/`-npm` builds; a monorepo's `rs-*`/`py-*` releases sharing
one version file) publish genuinely different artefacts that all declare the same label. Both are
the defined phenomenon — one `(input, version)` address denoting more than one published artefact —
but the second is a naming-scheme property, not an oversight.

Well-run projects are clean at their publication points. Drift belongs to two regimes: **continuous
publication under a hand-maintained label**, and **multi-artefact release schemes that reuse one
label across variants**.

## Send a result — the ask, and what you get for it

Everything in the reference table above is the author measuring **other people's repositories from
the outside**. Nobody outside the author has yet run this tool and reported a result from the
inside. `RESULTS.md` is the table for that, and as of this release **it is empty, published empty on
purpose**.

```bash
python3 closure_drift.py --json > result.json
```

Open a [**Report a measurement**](https://github.com/luizfnsilva/closure_drift/issues/new?template=measurement-result.yml)
issue with it, or send it to **lfnsilva.invest@gmail.com** if a public issue is not appropriate. One
command. The report carries counts, labels, hashes and the tool's own stamp — **never file
contents**, so a private repository can be measured without anything leaving your machine.

What you get back is in `RESULTS.md` in full, and briefly: your line in the table with attribution
as you choose it; a dated, version-pinned measurement you can cite when you claim your releases are
unambiguously addressed; and a straight answer about which mechanism produced your result.

**A result that contradicts the tool is worth more than one that confirms it**, and goes in the
table marked as such — there is a
[separate form](https://github.com/luizfnsilva/closure_drift/issues/new?template=false-positive.yml)
for it. A reference table that only ever agrees with its instrument is not evidence of anything.

## The report stamps itself

Every run reports the commit it measured and the hash of the tool that measured it:

```json
"stamp": {
  "measured_at_head": "1ea5e43618b4",
  "working_tree_dirty": false,
  "detector_closure": "14f6cbb4a0f65b7b"
}
```

Counts over repository history are functions of `HEAD`. We learned this the hard way: our own
headline count changed while the manuscript was open, because the commit that *fixed* the defect
created one more code state under the same label. The number was generated from artefacts, not
transcribed, and went stale anyway — because the measurement has a closure of its own and nothing
recorded it. A finding without the state it was measured in is a finding you cannot return to.

And once more, after 0.3.0 was deposited: an extended run was prepared with a working copy of this
very tool that had silently drifted behind the version deposited under its own DOI — older
semantics, same filename. The run was discarded and redone with the deposited bytes, checksum
verified against the Zenodo record before execution. The instrument exhibited the phenomenon it
measures. If you script this tool, pin the deposit and verify the checksum; the `CHANGELOG.md`
carries the incident.

## Tests

`tests/fixture_label_only.py` is the negative fixture: a synthetic repository with the shape of the
label-only ledger described above (one declared label, N commits each changing the published
content, no tags). It asserts that the tool (1) refuses to answer at the default when there are no
tags — exit 2, never a false `clean` — and (2) reports drift with one label covering N closures
under `--at commits`. Zero dependencies; `python3 tests/fixture_label_only.py`.

## Caveats

- The default closure globs are a guess. If they do not describe what determines your output, pass
  `--closure`. The tool prints what it used.
- Version auto-detection covers static declarations and the common dynamic-version layouts. If it
  cannot find your label it says so and exits `2` rather than reporting a number.
- `clean` means clean **over the range scanned**, at the points you told it about. It is not a proof
  — and it is a claim about addressing (A above), never about re-execution (B).

## Requirements

CPython **3.9 or later**, and `git` on `PATH`. No third-party packages, no network access, no
required configuration. The tool never writes to the repository it measures.

Tested on CPython 3.9 and 3.11, macOS and Linux.

## Repository-side configuration

A repository may commit its own measurement settings in `.closure-drift.json` at the root:

```json
{
 "at": "commits",
 "version_file": "path/to/file-holding-the-label",
 "version_regex": "\"version\"\\s*:\\s*\"([^\"]+)\"",
 "closure": ["src/composer.py", "src/catalogue*.json"]
}
```

Then `closure_drift.py` with no flags measures that repository the way it declares it should be
measured. CLI flags override the file; a broken file is an error, never silently ignored. Committing
the configuration makes the measurement itself reviewable — the flags become part of the
repository's history instead of someone's shell history.

## Version

**0.7.1** — see `CITATION.cff` and `CHANGELOG.md`. The measurement script changed in 0.7.0, for the
first time since 0.3.0: it is sha256
`6d8906ef374b73e6b8c58adba813c77c4ff352f5c9c280aa43ff2baa4f804451` here, against
`da5da3c0e781b67b9b3a55800d599c243edc8df649fc90b24a88e289533805c5` for 0.3.0 through 0.6.0. What
changed there is a refusal and not a measurement, and it was checked rather than asserted: the two
were run over the same repositories and every verdict field is identical. The one field that differs
is `detector_closure`, and it differs because the detector differs. **Every result produced under
0.3.0 through 0.6.0 remains valid and comparable**, and carries the closure of the detector that
produced it.

0.7.1 corrects this section and `CITATION.cff`: both still named 0.6.0 after the 0.7.0 release, which
was tagged and never deposited. 0.7 makes a malformed `--version-regex`, and one with no capture
group, a named refusal instead of an exception that left the process at the exit code for drift. 0.6
replaces the `LICENSE` file, which carried an abridged text of the Apache License while naming that
licence, with the unabridged one, and publishes the source repository; 0.5 added `SCOPE.md`, `NOTICE`
and `RESULTS.md`; 0.4 added the negative fixture, the (A)/(B) limitation above, three further
reference results, and the record of our own working-copy drift. Version 0.1 measured at every commit
and is superseded; if you have results from it, they overstate drift for any repository that
publishes at tags.

## Licence and citation

Apache-2.0, unabridged; the file deposited as 0.3.0 through 0.5.0 carried a shortened text under
that name and `CHANGELOG.md` records what was missing. See `LICENSE`, and `NOTICE` for the scope of
this release. Commercial use is
permitted with **no royalty and no payment obligation** — if you make money with this tool, you owe
nothing. `SCOPE.md` states what this tool does and what it will not be extended to do.
`CITATION.cff` carries the machine-readable citation.

Each deposited version gets its own DOI, and the deposit also has a concept DOI that always resolves
to the latest. **Cite the version DOI** if you are reporting a measurement — the tool's own output
records which version produced it, and a citation that does not pin the version cannot be checked
against that record.

The source is at **<https://github.com/luizfnsilva/closure_drift>**, where the files of this deposit
are held byte-identical to it under a checksum gate, so you can verify what you run without taking
anyone's word for it.

## Related

This is the detector for the first of six principles in an article about a production audit. The
other five have detectors described in the article; only this one is packaged.

It comes out of a longer research programme on measuring what a record can and cannot establish
about the thing it records. `SCOPE.md` marks where this tool stops, and that boundary is deliberate:
work on the far side of it — re-execution, attestation, provenance certification — exists but is not
this tool and will not arrive as a silent extension of it. If your problem lives there, write.
