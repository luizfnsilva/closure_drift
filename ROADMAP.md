# Roadmap

What is planned next, in order, and what is deliberately not planned. A change to the detector
ships with pre-registered proofs and an entry in `CHANGELOG.md`; nothing here is a promise of a date.

## Next

1. **Labels compared as versions, not as text.** `1.0` and `1.0.0` are one version to a package
   index and two labels here.
2. **Per-family verdicts in one run.** `--tags` measures one family; a monorepo wants the table.
3. **A closure that can include file modes**, opt-in, for projects where an executable bit is part
   of what is released.
4. **Annotations for pipelines other than GitHub's**, built from the same JSON report.

## Known problems, still open

- The default closure globs are a guess about what determines each project's output.
- Finding the label is a set of rules (`docs/LABELS.md`), not a build. 8 of the 100 repositories of
  the study are still undecided: versions computed from a tuple, and monorepos with no build file
  at the root.
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
