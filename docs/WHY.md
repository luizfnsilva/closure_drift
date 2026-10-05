# Why this tool exists

The README says what `closure_drift` does and how to run it. This page keeps the argument for why
the question matters, and the two incidents in which the author's own instrument showed the
phenomenon it measures.

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
checking can repair. The shape of that corpus is what this tool's negative fixture reproduces (see *Tests* below): a
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

## The report stamps itself

Every run reports the commit it measured and the hash of the tool that measured it:

```json
"stamp": {
  "measured_at_head": "1ea5e43618b4",
  "working_tree_dirty": false,
  "detector_closure": "6d8906ef374b73e6"
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
