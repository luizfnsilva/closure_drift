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
| `empty_closure`, `one_label`, `no_publication_points` | nothing in the closure; one label only; no tag to measure |
| `tag_names_no_version`, `prefix_names_no_package`, `unknown_ref` | about the tag or reference named |
| `bad_pattern`, `usage`, `broken_config`, `not_a_repository`, `git_unreadable` | about the input |

A code says why nothing was decided. It is not advice, and it does not decide anything.
