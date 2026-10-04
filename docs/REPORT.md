# The JSON report — `report_format: 2`

`closure_drift --json` prints one JSON object on standard output. This page is the contract for
it. Proof `K02` in `tests/battery.py` checks every report against the tables below.

## Three kinds of outcome, never confused

| kind | exit | how to recognise it |
|---|---|---|
| **a determination** | `0` or `1` | a report whose `verdict` is `clean` / `would_be_clean` (0) or `drift` / `would_drift` (1) |
| **not enough to determine** | `2` | a report whose `verdict` is `inconclusive`, `incomplete`, `no_labels`, `empty_closure`, `no_publication_points`, `no_label_at_head` or `empty_closure_at_head` |
| **an operational refusal** | `2` | **no JSON on standard output**; one or more lines on standard error naming the cause |

So: exit `1` always comes with a report saying `drift` or `would_drift`; exit `0` always comes with
`clean` or `would_be_clean`; and with exit `2`, standard output either holds a report with one of the
seven verdicts above or is empty. There is never a traceback.

## Fields of a measurement report (every verdict except `no_publication_points`)

| field | type | meaning |
|---|---|---|
| `report_format` | integer | `2` |
| `stamp.measured_at_head` | string | first 12 hex of `HEAD` |
| `stamp.working_tree_dirty` | `true` / `false` / `null` | `null` when it was not checked; then `stamp.working_tree_dirty_note` says why |
| `stamp.detector_closure` | string | first 16 hex of the SHA-256 of the detector that ran |
| `repo` | string | the path as passed on the command line |
| `version_file` | string | where the label was read from |
| `closure_globs` | list of strings | the globs used |
| `published_at` | `"tags"` / `"commits"` | |
| `verdict` | string | one of the verdicts above |
| `labels` | integer | distinct labels compared |
| `labels_covering_multiple_closures` | integer | labels in drift |
| `max_closures_per_label` | integer | |
| `drift` | object | label → { 16-hex closure → "tag (date)" where first seen } — only labels in drift |
| `closure_ids` | object | 16-hex closure → 64-hex identifier, for every closure in `drift` |
| `closure_changes_between_points` | integer | development churn; not drift |
| `publication_points` | integer | points with a non-empty closure |
| `publication_points_scanned` | integer | |
| `publication_points_compared` | integer | points that had both a label and a closure |
| `points_without_label` | integer | |
| `points_with_empty_closure` | integer | |
| `points_not_commits` | integer | tags that point at a blob or a tree |
| `range_truncated` | boolean | older points exist outside `--max-commits` |

Present only when relevant: `tag_globs` and `tags_filtered_out` (with `--tags`), `explain` (with
`--explain`: `label`, `first`, and `others[]` each with `changed`, `only_in_first`,
`only_in_other`).

## Fields of a `--would-tag` report

`report_format`, `stamp`, `mode` (`"would_tag"`), `repo`, `version_file`, `closure_globs`,
`published_at`, `verdict`, `label_at_head`, `closure_at_head`, `closure_id_at_head`,
`collides_with` (list of "tag (date)"), `existing_drift_labels`, and the six coverage fields above.

## `no_publication_points`

`report_format`, `verdict`, `note`.

## Compatibility

- Reports of 0.3.0–0.7.1 have no `report_format`; treat a missing field as `1`.
- Within `report_format: 2`, fields are only added. A field is removed or changes meaning only
  with a new `report_format`, announced in `CHANGELOG.md`.
- New verdicts may be added within a format, always at exit `2`. A consumer should treat an
  unknown verdict as "not determined".
- The 16-hex closure is computed by the formula of 0.3.0 and will not change within format 2.
