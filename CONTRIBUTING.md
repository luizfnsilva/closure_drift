# Contributing

## The most useful thing you can send is a measurement

```bash
python3 closure_drift.py --json > result.json
```

Open a [**Report a measurement**](../../issues/new?template=measurement-result.yml) issue with the
JSON, or send it to `lfnsilva.invest@gmail.com` if a public issue is not appropriate. The report
carries counts, labels, hashes and the tool's own stamp — **never file contents** — so a private
repository can be measured without its source leaving your machine.

`RESULTS.md` is the table those lines go into. It is published empty on purpose: as of the current
release nobody outside the author has run this tool and reported a result, and an empty table states
that fact instead of letting a reader assume otherwise.

**A clean result counts.** A table that only ever reports drift is not evidence of anything. And a
result showing the tool is **wrong about you** counts for more than either — it goes into the table
marked as a correction, not quietly discarded. That is what the
[false positive](../../issues/new?template=false-positive.yml) template is for.

## This repository and the Zenodo deposit

The citable artefact is the deposit; this repository is where it is developed and where results are
collected. Nine files here are byte-identical to the deposit, and `DEPOSIT.sha256` records their
hashes:

```bash
python3 tools/verify_deposit.py                # offline, against the manifest
python3 tools/verify_deposit.py --from-zenodo   # re-fetch the record and compare
```

CI enforces this on every push. If the two ever disagreed, a measurement citing the DOI could not be
checked against the code that produced it — which is precisely the failure this tool exists to
detect, happening in its own repository.

**So a pull request that edits one of those nine files cannot be merged as-is.** That is not a
rejection of the change; it means the change belongs to the next deposit. It is applied together
with a CHANGELOG entry, a new deposit, and a regenerated manifest, in one release. Say what you want
changed and it gets scheduled — do not work around the gate.

Everything outside the nine files — CI, issue templates, `tools/`, packaging, portability — is
ordinary and can be changed by ordinary pull request.

## What will not be accepted

`SCOPE.md` is the boundary, and it is the design rather than a list of gaps:

- **it never re-executes anything** — not your build, not your tests, not a recorded code state;
- **it attests nothing** — no certificate, no signature, no statement a third party is meant to rely
  on as proof;
- **it answers one question and stops.** A detector that keeps growing until it does everything ends
  up measuring nothing.

Anything on the re-execution / attestation / provenance-certification side is outside this tool by
design and will not arrive as a silent extension of it. If your problem lives there, say so — it can
be discussed, but not as a pull request to this file.

## If you do send code

Zero dependencies, standard library only, CPython 3.9 and later. The tool is read-only and must stay
that way: it must never write to the repository it measures, and must never require network access.

```bash
python3 tests/fixture_label_only.py   # the negative fixture must print "fixture ok"
python3 tools/verify_deposit.py       # the deposit must still verify
python3 closure_drift.py              # the tool measures this repository
```

A change to the measurement script changes what every past result means. If you propose one, say in
the pull request what it does to results already published — that sentence is the point of the
CHANGELOG, and a measurement whose instrument moved without saying so is the phenomenon this tool
exists to detect.

## Licence

Contributions are accepted under the Apache License, Version 2.0, the licence of this project. See
`LICENSE`, and `NOTICE` for the scope of the release.
