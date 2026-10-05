# Roadmap

What is planned next, in order, and what is deliberately not planned. A change to the detector
ships with pre-registered proofs and an entry in `CHANGELOG.md`; nothing here is a promise of a date.

## Next

From `docs/FAILURES.md`, in the order they hurt:

1. **`clean` must say how much it rests on** (O1). A share of tags compared below which the
   answer is `incomplete` without `--strict`.
2. **Tree objects released as the scan moves on** (O4), and a refusal for want of a label before
   the scan, not after (O5).
3. **Components declared in the config file** (O2, O3): a version file, a closure and a tag
   pattern per package, one verdict each. Declared, never inferred.
4. **The glob language written down and frozen** (O6), with the exclusions matching files only.
5. Labels compared as versions (`1.0` = `1.0.0`); file modes in the closure, opt-in.

## Known problems, still open

`docs/FAILURES.md` is the list. Not measured: repositories beyond 190,000 files, Windows at that
size, network file systems, git older than 2.24.

## Small, self-contained tasks — a good place to start

- Add `go.mod`, `Chart.yaml` or `*.gemspec` to the version sources, each with a battery proof.
- A proof for a tag that points at an annotated tag that points at a commit.
- `--badge` for `--at commits`.
- Translate nothing: the tool's output is English only, by decision.

## Not planned

Rebuilding anything, signing anything, attesting anything, or judging a release process. See
`SCOPE.md`. This tool complements release immutability and supply-chain attestation; it does not
replace them.
