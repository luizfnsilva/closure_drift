# The JSON consumer study (§38) — result

Pre-registered in `tests/PREREGISTRATION.md` §38 (commit e230e09) before any consumer was read. Detector 1.11.0
(sha256 `0626fe82…`).

## Decision

**No class-C ambiguity was shown. There is no 2.0: 1.11 is the last functional release, and the freeze of §36
starts.** Three class-A items were fixed in `docs/REPORT.md`; no class-B item was found. One consumer defect (not an
ambiguity of the contract) is recorded below.

## Amendment 1 (written before any hit was decided)

The two strings fixed in §38 collide with unrelated uses ("closure drift" in physics, CI and audit tooling: 1,292 and
1,148 hits; the search API returns at most 1,000 per query). A hit was therefore taken as touching this tool only
if it also names it; four queries were added for that: `"luizfnsilva/closure_drift"`, `"closure_drift.py"`,
`"closure-drift --json"`, `"closure_drift --json"`, plus `"io.github.luizfnsilva"` and `closure_ids`.

## Consumers

**External: zero.** The hits outside `luizfnsilva` that name the tool are listings (`linny006/mcp-servers-live`,
`rogerchappel/mcpchangefeed`, `leipzig/awesome-reproducible-research`, `subev/awesome-stars`,
`Arnon-hs/open-source`); none reads a report. `closure_ids` hits (5,040) are other software. Not concluded: none
among the hits that name the tool; the colliding hits beyond the first 1,000 of each query were not read.

**Internal: nine.** Fields read, and whether two readings consistent with the contract give different behaviour:

| consumer | fields read | result |
|---|---|---|
| `action.yml` | `verdict`, exit, `note`, `drift`, `label_at_head`, `collides_with`, `tag`, `label_at_tag`, `version_written_at_publish`, `version_files_not_read`, `contradicted_sources`, `points_with_empty_closure`, `publication_points_scanned`, `stamp.*`, summary counts | A1, A2 (below); defect D1 |
| `closure_drift_mcp.py` (both copies) | exit only; the report is passed through | unambiguous |
| `closure_verify.py` | `report_format`, `mode`, `verdict`, `drift`, `closure_ids`, `closure_commits`, `closure_globs`, `closure_modes`, counts | unambiguous (keys `~n` read from `docs/VERDICTS.md`; see A2) |
| `tools/regression/regress.py` | `verdict`, `drift`, `closure_ids`, `drift_mechanism`, `reason_code`, verifier output | unambiguous |
| `examples/demo.py` | `verdict`, exit | unambiguous |
| `skills/closure-drift/SKILL.md` | exit and `verdict` of `--would-tag`, `--tag`, full run | unambiguous (it states `tag_mismatch` is exit 1) |
| GitLab template, `integrations/`, `docs/` | exit only | unambiguous |

## Contract pass

Every top-level and `stamp.` field of the eight `docs/report-examples/` and of the 99 corpus reports of run
43862463677 (`regression-check/consumers38`, `--reports`; `apache/arrow` not checkable) is documented. Corpus:
59 `clean`/0, 29 `drift`/1, 4 `incomplete`/2, 1 `inconclusive`/2, 6 refusals (exit 2, no JSON); all 93 reports
`published_at: "tags"`; 225 `drift` values of the form `tag (date)`; no `~n` key.

## Items

- **A1 — exit 1 and 0 of `--tag`.** The table "Three kinds of outcome" listed no `tag_mismatch`/`tag_matches`, and
  said exit 1 always means one label covers more than one closure. A `--tag` run on a tag whose commit declares
  another version prints `tag_mismatch`, exit 1 (reproduced). Fixed by wording.
- **A2 — the value and key of `drift`.** Documented as `"tag (date)"` and a 16-hex key. With `--at commits` the value
  is the commit's first message line (`{"1.0": {"732033b6ebb34ecb": "a (2026-11-16)", …}}`, reproduced), which can
  look like a tag; `published_at` tells them apart. A key can be `short~n` (`docs/VERDICTS.md`); no printed report
  carries one, so that half does not count under §38 and is fixed only as wording. Fixed by wording.
- **A3 — the components report carries `stamp`**, which its field list omitted (reproduced). Fixed by wording.
- **D1 — consumer defect, `action.yml`.** On a components report in drift (top-level `verdict: "drift"`, exit 1,
  no top-level `drift`), the Action fails the step and prints DRIFT but annotates no label, because it reads only
  the top-level `drift`. The contract is clear; the consumer does not read `components`. A proven bug: may be fixed
  under the freeze, separately.
