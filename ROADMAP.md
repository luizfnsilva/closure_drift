# Roadmap

What is planned next, in order, and what is deliberately not planned. A change to the detector
ships with pre-registered proofs and an entry in `CHANGELOG.md`; nothing here is a promise of a date.

## Next

Done in 1.1.0: `--published` (O10, and O2a with the list), the refusal before the scan (O5),
`--label-equality` and `--modes` (O7), `--at commits` voted by tags (O2c), `Chart.yaml`, gemspec
and `go.mod` (O3).

From `docs/FAILURES.md`, still open: more version sources (O3), each with a proof, when someone
asks for one; a measurement by someone else in `RESULTS.md` (O9).

## Known problems, still open

`docs/FAILURES.md` is the list. Not measured: repositories beyond 190,000 files, Windows at that
size, network file systems, git older than 2.24.

## Small, self-contained tasks — a good place to start

- Add another ecosystem's version file to the rules (`mix.exs`, `pubspec.yaml`, `*.csproj`…), with
  a battery proof and a mutant.
- Translate nothing: the tool's output is English only, by decision.

## Not planned

Rebuilding anything, signing anything, attesting anything, or judging a release process. See
`SCOPE.md`. This tool complements release immutability and supply-chain attestation; it does not
replace them.
