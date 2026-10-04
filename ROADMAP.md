# Roadmap

What is planned next, in order, and what is deliberately not planned. A change to the detector
ships with pre-registered proofs and an entry in `CHANGELOG.md`; nothing here is a promise of a date.

## Next

1. **Read the version a tag-derived project would be built with.** 0.9.0 says when a version comes
   from the tag (`setuptools_scm`, `hatch-vcs`) and stops there. Whether there is anything to
   measure for those projects — the tag is the label — is an open question, not a missing flag.
2. **Per-family verdicts in one run.** `--tags` measures one family; a monorepo wants the table.
3. **A closure that can include file modes**, opt-in, for projects where an executable bit is part
   of what is released.
4. **Annotations for pipelines other than GitHub's**, built from the same JSON report.

## Known problems, still open

- The default closure globs are a guess, and the study in `tools/study/` shows how often the
  default version source reads the wrong file (7 of 21 drift results). Better defaults need
  evidence about what determines each ecosystem's output, not more patterns.
- A change of file mode alone, and anything under the excluded folders, is not seen (`SCOPE.md`).
- `RESULTS.md` is empty: nobody outside the author has reported a measurement yet.
- Not measured: repositories with more than a few hundred thousand files, network file systems,
  git older than 2.24.

## Small, self-contained tasks — a good place to start

- Add `go.mod`, `Chart.yaml` or `*.gemspec` to the version sources, each with a battery proof.
- A proof for a tag that points at an annotated tag that points at a commit.
- `--badge` for `--at commits`.
- Translate nothing: the tool's output is English only, by decision.

## Not planned

Rebuilding anything, signing anything, attesting anything, or judging a release process. See
`SCOPE.md`. This tool complements release immutability and supply-chain attestation; it does not
replace them.
