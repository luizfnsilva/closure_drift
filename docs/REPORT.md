# The JSON report — `report_format: 2`

`closure_drift --json` prints one JSON object on standard output. This page is the contract for
it. Proof `K02` in `tests/battery.py` checks every report against the tables below.

## Three kinds of outcome, never confused

| kind | exit | how to recognise it |
|---|---|---|
| **a determination** | `0` or `1` | a report whose `verdict` is `clean` / `would_be_clean` / `identical` / `differs_under_two_labels` (0) or `drift` / `would_drift` / `differs_under_one_label` (1) |
| **not enough to determine** | `2` | a report whose `verdict` is `inconclusive`, `incomplete`, `no_labels`, `empty_closure`, `no_publication_points`, `no_label_at_head`, `empty_closure_at_head` or `not_comparable` |
| **an operational refusal** | `2` | **no JSON on standard output**; one or more lines on standard error naming the cause |

So: exit `1` always comes with a report saying one label covers more than one closure; exit `0`
always comes with a report saying none does; and with exit `2`, standard output either holds a
report with one of the eight undetermined verdicts or is empty. There is never a traceback. (One
exception to "empty": with `--diagnose` and without `--json`, the diagnostics block is printed
before a refusal — that is what it is for.)

## Fields of a measurement report (every verdict except `no_publication_points`)

| field | type | meaning |
|---|---|---|
| `report_format` | integer | `2` |
| `stamp.measured_at_head` | string | first 12 hex of `HEAD` |
| `stamp.working_tree_dirty` | `true` / `false` / `null` | `null` when it was not checked; then `stamp.working_tree_dirty_note` says why |
| `stamp.detector_closure` | string | first 16 hex of the SHA-256 of the detector that ran |
| `repo` | string | the path as passed on the command line |
| `version_file` | string or `null` | where the label is read from at `HEAD` |
| `closure_globs` | list of strings | the globs used |
| `published_at` | `"tags"` / `"commits"` | |
| `verdict` | string | one of the verdicts above |
| `labels` | integer | distinct labels compared |
| `labels_covering_multiple_closures` | integer | labels in drift |
| `max_closures_per_label` | integer | |
| `drift` | object | label → { 16-hex closure → "tag (date)" where first seen } — only labels in drift |
| `closure_ids` | object | 16-hex closure → 64-hex identifier, for every closure in `drift` |
| `closure_changes_between_points` | integer | development churn; not drift |
| `label_sources` | object | where labels were read from → number of points; `"(the tag)"` when the version is derived from the tag |
| `points_with_conflicting_sources` | integer | points where the source changed and the earlier file still declares another version; never `clean` when above zero |
| `points_label_contradicted` | integer | (0.10.0) points whose label came from a file no tag named for a version agrees with; counted in `points_without_label`; never `clean` when above zero |
| `contradicted_sources` | list of strings | (0.10.0) those files; present only when not empty. They are left out of `label_sources` |
| `publication_points` | integer | points with a non-empty closure |
| `publication_points_scanned` | integer | |
| `publication_points_compared` | integer | points that had both a label and a closure |
| `points_without_label` | integer | |
| `points_with_empty_closure` | integer | |
| `points_not_commits` | integer | tags that point at a blob or a tree |
| `range_truncated` | boolean | older points exist outside `--max-commits` |

Present only when relevant: `tag_families` (prefix → count, when the tags in drift carry two or
more prefixes), `diagnostics` (with `--diagnose`, in every kind of report: `detector_version`,
`detector_closure`, `python`, `platform`, `git`, `options`, `repository`, and from 1.0.0 `objects_read`,
the number of git objects the run read), `component` (with `--component`), `tag_globs` and `tags_filtered_out` (with `--tags`), `explain` (with
`--explain`: `label`, `first`, and `others[]` each with `changed`, `only_in_first`,
`only_in_other`).

## Fields of a `--would-tag` report

`report_format`, `stamp`, `mode` (`"would_tag"`), `repo`, `version_file`, `closure_globs`,
`published_at`, `verdict`, `label_at_head`, `closure_at_head`, `closure_id_at_head`,
`label_source`, `collides_with` (list of "tag (date)"), `existing_drift_labels`, `label_at_head_rejected`
(0.10.0, present when the label at HEAD came from a contradicted file: `{"label", "source"}`), and the coverage fields above;
with `--tags`, also `tag_globs` and `tags_filtered_out`. `--would-tag` looks at every tag, so its
`range_truncated` is always `false`.

## Fields of a `--compare` report

`report_format`, `stamp`, `mode` (`"compare"`), `repo`, `version_file`, `closure_globs`, `verdict`,
`a` and `b` (each: `ref`, `commit`, `label`, `label_source`, `closure`, `closure_id`, `files`), `changed`,
`only_in_a`, `only_in_b`.

## `no_publication_points`

`report_format`, `verdict`, `note`.

## An example of every kind

[`report-examples/`](report-examples/) holds one real report of each kind — `clean`, `drift`, `drift`
with `--explain`, `inconclusive`, `no_publication_points`, `would_drift`, `would_be_clean` and
`--compare` — printed by the detector on tiny repositories built with fixed dates.
`tools/make_report_examples.py --check` runs in CI and fails when they differ from what the detector
prints, so they cannot go stale.

## What prints no report

`--help`, `-h` and `--version` print their text and end at `0`, as every command-line program does.
They are not measurements and carry no verdict.

## Compatibility

- Reports of 0.3.0–0.7.1 have no `report_format`; treat a missing field as `1`.
- Within `report_format: 2`, fields are only added. A field is removed or changes meaning only
  with a new `report_format`, announced in `CHANGELOG.md`.
- New verdicts may be added within a format, always at exit `2`. A consumer should treat an
  unknown verdict as "not determined".
- The 16-hex closure is computed by the formula of 0.3.0 and will not change within format 2.

## Components (1.0.0)

With `components` in `.closure-drift.json` and no `--component`: `report_format`, `mode`
(`"components"`), `repo`, `measured_at_head`, `verdict` (`drift` if any component is in drift,
`clean` if every one is clean, otherwise `incomplete`), and `components`: name → that component's
report, with its own `exit`; a component that was refused is `{"verdict": "refused", "exit": 2,
"note"}`. With `--component NAME`, the ordinary report of that component with `"component": NAME`;
a flag on the command line overrides that component's setting, as it does at the top level.
