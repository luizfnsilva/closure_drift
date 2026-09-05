# Third-party results

Every measurement in this file was produced by **someone other than the author**, on a repository
the author does not control, and is reproducible by anyone with the same deposit and the same
commit.

That is the point of the file. The reference table in the README is the author measuring other
people's repositories from the outside. This table is other people measuring their own, from the
inside, where the author cannot reach — including private repositories whose contents never leave
their machine, because the tool is read-only, needs no network, and the JSON report contains no
source code.

## How to add a line

```bash
python3 closure_drift.py --json > result.json
```

Open a [**Report a measurement**](https://github.com/luizfnsilva/closure_drift/issues/new?template=measurement-result.yml)
issue with it, or send it to **lfnsilva.invest@gmail.com** if a public issue is not appropriate. That
is the whole ask. It takes one command and reveals nothing about your code: the report carries
counts, labels, hashes and the tool's own stamp — never file contents, never file paths outside
what you chose to declare as your closure.

**What you get back, and it is not a favour — it is the trade:**

- **your line in this table**, with attribution exactly as you want it: your name, your
  organisation's name, a handle, or `anonymous`. Your call, stated when you send it;
- **citable provenance for your own claim.** If you publish anything that says your releases are
  unambiguously addressed, this gives you a dated measurement, produced by a version-pinned
  instrument with its own DOI, that a reviewer can re-run. Saying it is cheap; having the artefact
  is not;
- **a straight answer about your result.** If your repository drifts, which of the two known
  mechanisms it is — a release tagged without bumping the version file, or label collision across
  tag families — and whether it matters for how you publish. If it is neither, that is more
  interesting than a clean run and it will be said so;
- **a correction, publicly, if the tool is wrong about you.** A result that shows the detector
  misreading a legitimate scheme is the most valuable thing this file can receive, and it goes in
  the table marked as such, not quietly discarded.

Results that **contradict** the tool are as welcome as results that confirm it, and are marked in
the table rather than dropped. A reference table that only ever agrees with its instrument is not
evidence of anything.

## What is required for a line to count

- the **version DOI** of the deposit used, not the concept DOI — a measurement whose instrument
  version is unknown cannot be checked against the report that produced it;
- the **`stamp` block** as the tool emitted it (`measured_at_head`, `working_tree_dirty`,
  `detector_closure`);
- whether the run used the default (`--at tags`) or `--at commits`, and any `--closure` you passed;
- a repository anyone can reach, **or** a statement that it is private — private results are
  accepted and marked `private`, with counts but no repository name.

Counts over repository history are functions of `HEAD`. A line without its stamp is a number
without the state it was measured in, and this project does not publish those.

## The table

| Date | Repository | Reported by | Points | Labels | Worst label | Verdict | Deposit |
|---|---|---|---|---|---|---|---|
| — | *no third-party results yet* | — | — | — | — | — | — |

**This table is empty, and it is published empty on purpose.** As of this release nobody outside the
author has run this tool and reported a result. Leaving the row out entirely would let a reader
assume otherwise; an empty table states the fact. When it fills, the fact it states changes — and
that change is the only thing that would let this project claim it has been reproduced by anyone
else.
