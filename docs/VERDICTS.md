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
