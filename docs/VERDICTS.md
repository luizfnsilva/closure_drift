# Where each verdict is decided

One function per answer. Read it to see every rule behind a verdict.

| verdict | exit | decided in |
|---|---|---|
| `clean`, `drift`, `incomplete`, `empty_closure`, `no_labels`, `inconclusive` | 0, 1, 2 | `decide()` (tags or commits scan) |
| `no_publication_points` | 2 | `measure()`, before the scan |
| `tag_matches`, `tag_mismatch`, `incomplete` | 0, 1, 2 | `check_tag()` (`--tag`) |
| `would_be_clean`, `would_drift`, `incomplete`, `no_label_at_head`, `empty_closure_at_head` | 0, 1, 2 | `would_tag()` (`--would-tag`) |
| `identical`, `differs_under_two_labels`, `differs_under_one_label`, `not_comparable` | 0, 1, 2 | `compare()` (`--compare`) |
| `refused` (one component) | 2 | `components()` |

A scan runs in this order: `prepare()` (version source, pattern, closure; refuses bad input) →
`scan()` (each publication point; refuses when no label is found) → `assemble()` (report fields) →
`decide()` → `report()` (badge, JSON or text). Refusals print the reason and exit 2; they are raised
where the input is read, not in `decide()`.

## Reason codes (1.10)

An undetermined verdict carries `reason_code` in its JSON; every refusal and every undetermined verdict ends
stderr with `reason: CODE`. A decided verdict (exit 0 or 1) carries none.

| code | meaning |
|---|---|
| `no_version_source` | no file the rules read declares a version |
| `version_outside_component` | none at the root, but a manifest one level down |
| `version_written_at_publish` | a workflow at that commit writes the version from the tag (named on the first line) |
| `version_from_tag` | the version is derived from the tag at build time |
| `source_contradicted`, `sources_conflict`, `source_too_large` | the source is contradicted by the tags, disagrees with another, or was too large to read |
| `strict_uncovered`, `too_few_compared` | `--strict` and a point not compared; fewer points compared than not |
| `shallow_history` | (1.11.1) `--at commits` in a shallow clone, no label in drift among the commits it holds |
| `empty_closure`, `one_label`, `no_publication_points` | nothing in the closure; one label only; no tag to measure |
| `tag_names_no_version`, `prefix_names_no_package`, `unknown_ref` | about the tag or reference named |
| `bad_pattern`, `usage`, `broken_config`, `not_a_repository`, `git_unreadable` | about the input |

A code says why nothing was decided. It is not advice, and it does not decide anything.

## The closure, as a verifier must reproduce it (1.11, §37)

`closure_verify.py` is written from this section, not from the detector's code.

- **Entries.** `git ls-tree -r -z --full-tree <commit>`, in that order: files (`blob`) and submodule pointers
  (`commit`). Paths are bytes, decoded UTF-8 with `surrogateescape`.
- **Glob match** (`fnmatch.fnmatchcase`, where `*` crosses `/`): a path matches a glob `g` when it matches `g`;
  or `g` with every `**/` written `*/`; or, when `g` starts with `**/`, the rest of `g`; or, when `g` ends with
  `/**`, the path starts with `g` minus `**`.
- **Never in it:** `**/test/**`, `**/tests/**`, `**/*_test.*`, `**/*.test.*`, `**/spec/**`, `**/docs/**`,
  `**/*.md`, `**/node_modules/**`, `**/vendor/**`, `**/.git/**`. A pattern `**/X` with no `/` in `X` is a file
  pattern: it excludes a file whose own name matches `X`, and never a submodule pointer. Every other pattern
  excludes a path that glob-matches it.
- **Brought back in** (§29): an excluded path is in when no file pattern excludes it, `.git` is not one of its
  folders, it lies in at least one of `test`, `tests`, `spec`, `docs`, `vendor`, `node_modules`, and some
  include glob both matches it and names every one of those folders it lies in. A file's folders are its path
  segments but the last; a submodule pointer's are all of them.
- **Member:** matches an include glob of `closure_globs` and is not excluded, or is brought back in.
- **Ids.** Over the members in entry order: the short id is the first 16 hex of SHA-256 over `path id` with
  nothing between; the full id is SHA-256 over `path NUL kind SP id LF`, with ` mode` (the six digits from
  `ls-tree`) before `LF` when `closure_modes` is true. A key is the short id, or `short~n` when another closure
  of the same label had that short id first.
