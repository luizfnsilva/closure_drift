# Start here

Four questions. Each answer is a few lines; the details are in [`USAGE.md`](USAGE.md).

## 1. Does it fit your repository?

| how your version is set | fit |
|---|---|
| in a file you commit before tagging (`pyproject.toml`, `Cargo.toml`, `package.json`, …) | yes |
| derived from the tag (setuptools-scm, hatch-vcs, …) | the history check only; `--tag` has little to compare |
| written into the file by the release job (`uv version "$GITHUB_REF_NAME"`, `sed`, a script) | no. `--tag` answers `incomplete` on every release, or, when a script writes it, a `tag_mismatch` that is not real |
| you do not tag releases | not yet |

It checks the repository: what a tag points at and what that commit declares. It does not check a
built package. For that, use the package's own metadata, checksums, and build provenance
(for example GitHub artifact attestations). The two are complementary.

## 2. Which mode?

| you want to | run | in CI |
|---|---|---|
| check a repository's history once | `closure_drift .` | `mode: measure` on a schedule |
| check a tag you just pushed | `closure_drift . --tag v1.2.0` | `mode: auto` on tag push |
| gate a release pipeline | `--would-tag` before tagging, `--tag` after | the publish job `needs:` the check ([example](https://github.com/luizfnsilva/closure-drift-release-examples#gate-a-publish-job-behind-the-check)) |

A check that the publish job does not depend on only observes the release. With `needs:`, a failed
check stops the publish job. A check run after the tag is pushed cannot undo the tag.

## 3. What does the answer mean?

| exit | meaning |
|---|---|
| 0 | the label names one state of the code, for the files in the closure |
| 1 | a label names two states: do not publish |
| 2 | nothing was decided. **Not a pass**: the report says why, and `Next:` says what to do |

## 4. What next?

The last line of every report starts with `Next:`. On exit 2 it names the cause: the file to pass
with `--version-file`, the globs to pass with `--closure`, `--diagnose`, or, when the release job
writes the version, the workflow file and line. Each cause is listed in
[`USAGE.md`](USAGE.md#when-the-answer-is-exit-2).

A folder renamed after some releases: `--closure 'old/**'` still measures the older tags, and
`--would-tag` answers exit 2 at the new commit. Pass both globs.
