# Roadmap

What is planned next, in order, and what is deliberately not planned. A change to the detector
ships with pre-registered proofs and an entry in `CHANGELOG.md`; nothing here is a promise of a date.

## Next

1. **Compare two references** — `--compare A B`: which paths of the closure differ between two
   tags or commits, named unambiguously. `--explain` answers this only for a label already in
   drift; `--would-tag` names the colliding tag and not what differs.
2. **`--diagnose`** — one block to paste into a bug report: detector version and hash, git
   version, the options in effect, how many references were examined, what could not be read.
   No file contents and no paths inside the closure.
3. **Tag families found automatically** — suggest `--tags` globs when the drift in a repository
   is explained by tag prefixes sharing one version file.
4. **Version labels that come from the tag** — projects built with a version derived from the
   tag itself have no version file to read; say so by name instead of "no label found".

## Small, self-contained tasks — a good place to start

- Add `go.mod`, `Chart.yaml` or `*.gemspec` to the version sources, each with a battery proof.
- A proof for a tag that points at an annotated tag that points at a commit.
- `--badge` for `--at commits`.
- Translate nothing: the tool's output is English only, by decision.

## Not planned

Rebuilding anything, signing anything, attesting anything, or judging a release process. See
`SCOPE.md`. This tool complements release immutability and supply-chain attestation; it does not
replace them.
