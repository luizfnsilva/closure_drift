# What the evidence is, and what it may be cited for

Two bodies of evidence, kept apart, because they answer different questions.

## Exploratory: real repositories

The 100 most-downloaded PyPI projects with a public repository (`tools/study/`), and six reference
repositories (`tools/reference/`). They say **how often** a version label names more than one state
of the code in practice (29 of the 88 decided, at the defaults) and **where** the rules find or miss
a label.

They are **not** a measure of accuracy. Their answers are the tool's own; nobody established the
right answer for each repository independently. Each collision can be checked by hand
(`tools/study/collisions.tsv`, one line per tag), and some were, but that is checking, not a
labelled benchmark. The same repositories, pinned, are the regression corpus (`tools/regression/`):
it says a release **still gives the recorded answer**, not that the answer is right.

May be cited for: incidence in that population; that a release did not change its answers.

## Reference: cases whose right answer was written first

| suite | what is fixed before the run | what it says |
|---|---|---|
| `tests/battery.py` | each proof's required verdict and exit code, in `tests/PREREGISTRATION.md` | the detector gives the right answer on these cases, including `incomplete` and refusals where it must not decide |
| `tests/negative_controls.py` | each mutant, and the proof that must catch it | the battery fails when the detector is broken in those ways |
| `tests/adversarial.py` | cases written by reviewers who did not write the fixes | 304 of 315 as required; the 2 loose are declared limits (`docs/FAILURES.md`) |
| `tests/properties.py` + `tests/oracle.py` | an independent implementation from a specification | the two agree on 60 generated repositories, for 17 properties |

Scores per platform: `tests/RECORD.md`. Never added together.

May be cited for: correctness **on those cases**, including not approving what it cannot decide.
Not for inputs nobody tried.

## People and agents

- Third-party measurements: `RESULTS.md`. Evidence of use; a result counts as evidence of detection
  only when the reporter confirmed it independently.
- How an agent behaves with the check: `tools/agents/results/` (pilots of `tests/PREREGISTRATION.md`
  §23; one agent, one run per case: what can happen, not how often).
- How people read the output: `docs/USABILITY.md` (a protocol, not yet run).
