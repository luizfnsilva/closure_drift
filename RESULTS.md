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
is the whole ask. It takes one command and reveals very little about your code: the report carries
counts, labels, hashes and the tool's own stamp — never file contents. It does carry paths: the
repository path exactly as you passed it on the command line, and the paths of the files the label
was read from, which can be inside your closure; with `--explain` or `--compare`, the paths that
differ. If any is sensitive, run the tool from inside the repository so the first is `.`, and read
the JSON before you send it.

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
| 2026-10-22 | private ([#13](https://github.com/luizfnsilva/closure_drift/issues/13)) | anonymous | 101 commits | 1 | `0.1.0`: 91 closures | `drift`, under `--at commits` as a diagnostic: the reporter did not confirm that each commit is a publication | 1.1.3, [10.5281/zenodo.23458648](https://doi.org/10.5281/zenodo.23458648) |
| 2026-10-27 | private (sent by e-mail) | anonymous | 2 commits | 1 | `0.1.0`: 1 closure | `inconclusive`: one label, nothing to compare yet | 1.2.0, [10.5281/zenodo.23557140](https://doi.org/10.5281/zenodo.23557140) |

Stamps, as the tool emitted them:

- 2026-10-22: `measured_at_head` `41f61ded5da6`, `working_tree_dirty` false, `detector_closure`
  `101905f660655bda`; `--at commits --version-file package.json`, default closure. With the
  default `--at tags` the answer was `no_publication_points`: the repository has no tags.
- 2026-10-27: `measured_at_head` `40a504018fb2`, `working_tree_dirty` false, `detector_closure`
  `7dd5833ccb6c16bf`; `--at commits --version-file package.json`, default closure. Without
  `--version-file` no label was found: `package.json` is marked private, and the refusal did not
  say so. 1.2.1 says so (`tests/PREREGISTRATION.md` §21).

Neither result contradicts the tool. The first report of use
([#12](https://github.com/luizfnsilva/closure_drift/issues/12), two projects, both `drift` under
`--at commits`) is not in the table yet: it waits for the reporter's attribution and stamps.
