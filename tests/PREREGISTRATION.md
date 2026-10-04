# Pre-registration — closure_drift 0.8.0 batteries

Written on 2026-10-04, **before** the detector was changed and before any case below was run.
Each line states what is done and the outcome required. A line is never rewritten after a run:
if an expectation turns out to be wrong, the original stays and a dated amendment is added in §6.

Three batteries, each with its own polarity. Their scores are reported side by side and are
**never added together**.

- `tests/battery.py` — acceptance proofs (§1–§2): each is `green`, `red` or `not_run` (with a
  named reason, when the platform cannot do what the proof needs).
- `tests/negative_controls.py` — the battery is run against deliberately broken copies of the
  detector (§3); each mutant must turn the named proofs red. A battery that stays green on a
  broken detector proves nothing.
- `tests/adversarial.py` — hostile inputs (§4, pre-registered separately in
  `PREREGISTRATION_ADVERSARIAL.md` by whoever writes that campaign).

The existing `tests/fixture_label_only.py` is kept unchanged and must keep passing (proof H01).

## 0. What 0.7.1 does, measured on 2026-10-04, that this release changes

| # | measured on 0.7.1 | required from 0.8.0 |
|---|---|---|
| X1 | a file whose name is not ASCII is silently left out of the closure; two tags, one label, only `src/ação.py` changed → `inconclusive`, exit 0 (the same case with `acao.py` → `drift`) | in the closure; `drift`, exit 1 |
| X2 | `.closure-drift.json` holding `[]`, or bytes that are not UTF-8 → traceback, exit 1 (the code for drift) | named refusal, exit 2 |
| X3 | `inconclusive` and `no_labels` end at exit 0 | exit 2; exit 0 means `clean` and nothing else |
| X4 | tags without a version label, and tags where the closure is empty, are skipped without a word; a failing `git` call is read as empty output | counted and printed; a failing `git` call is a named refusal, exit 2 |
| X5 | `core.fsmonitor` set in the measured repository's config is executed (the detector runs `git status`) | not executed |
| X6 | a version label holding a line break prints a forged line in the text report | control characters are escaped in everything printed |
| X7 | `"closure": "src/**"` (a string) is iterated character by character | named refusal, exit 2 |
| X8 | `--max-commits` zero or negative changes the range without saying so | named refusal, exit 2 |
| X9 | `--version-regex` without a version file is discarded in silence | named refusal, exit 2 |
| X10 | a submodule pointer inside the closure is ignored | part of the closure |

## 1. Exit codes — the closed set required from 0.8.0

| code | meaning |
|---|---|
| `0` | verdict `clean`, and only that |
| `1` | verdict `drift` |
| `2` | no determination, cause named: a refusal on stderr, or one of the verdicts `inconclusive`, `no_labels`, `empty_closure`, `no_publication_points` in the report |

No input may produce a traceback, and no failure may end at `1`.

## 2. Acceptance proofs

**A — verdicts**

| id | setup | required |
|---|---|---|
| A01 | two tags, two labels, two closures | `clean`, exit 0 |
| A02 | two tags, one label, two closures | `drift`, exit 1, 1 label covering 2 closures |
| A03 | two tags, one label, the same closure | `inconclusive`, exit 2 |
| A04 | one tag | `inconclusive`, exit 2 |
| A05 | commits, no tags, default `--at` | `no_publication_points`, exit 2 |
| A06 | 6 commits changing the closure, one label, `--at commits` | `drift`, exit 1, max 6 closures |
| A07 | closure globs that match nothing at any tag | `empty_closure`, exit 2 |
| A08 | version regex that matches at no tag | `no_labels`, exit 2 |
| A09 | three tags: labels 1, 2, 2 with the two `2` differing in closure | `drift`; `labels` 2, `labels_covering_multiple_closures` 1 |

**B — what was not compared is said**

| id | setup | required |
|---|---|---|
| B01 | 4 tags, the first 2 without the version file | `clean`, exit 0, `points_without_label` = 2, and the text report prints that count |
| B02 | 3 tags, the first with nothing matching the closure | `points_with_empty_closure` = 1 |
| B03 | 5 tags, `--max-commits 3` | `publication_points_scanned` = 3, `range_truncated` = true, the text report says so |
| B04 | a tag that points at a blob, among ordinary tags | run completes; `points_not_commits` = 1 |

**C — paths**

| id | setup | required |
|---|---|---|
| C01 | X1: only `src/ação.py` changes between two tags, one label | `drift`, exit 1 |
| C02 | only a file with a space and a tab in its name changes | `drift` |
| C03 | only a file with a line break in its name changes | `drift`; `not_run` where the file system refuses the name |
| C04 | X10: only a submodule pointer under `src/` changes | `drift` |
| C05 | ASCII-only repository | every closure equals the value computed by the 0.3.0–0.7.1 formula, written independently in the battery: SHA-256 over `path` + `blob id` in `ls-tree` order, first 16 hex |
| C06 | only a file whose name is not valid UTF-8 changes | `drift`; `not_run` where the file system refuses the name |

**D — refusals: exit 2, cause named on stderr, no traceback**

| id | input |
|---|---|
| D01 | a directory that is not a git repository |
| D02 | config file is `[]` |
| D03 | config file is not UTF-8 |
| D04 | config file is not JSON |
| D05 | config file with an unknown key (`"closures"`) |
| D06 | config `"closure"` is a string |
| D07 | config `"at": "weekly"` |
| D08 | `--version-regex '('` with a version file |
| D09 | `--version-regex 'version'` (no group) with a version file |
| D10 | `--version-regex` without any version file |
| D11 | `--max-commits 0`, and `--max-commits -3` |
| D12 | repository with no recognisable version file |
| D13 | `git` not on `PATH` |
| D14 | a tree object of a tagged commit deleted from the object store: the run must refuse, naming git — never complete with that tag skipped |
| D15 | an exception raised inside the measurement (injected) → exit 2, a line naming an internal error, no traceback |
| D16 | repository with no commits |

**E — what is printed**

| id | setup | required |
|---|---|---|
| E01 | X6: a label holding a line break, an ANSI escape and a forged `CLEAN:` line | the text report contains no control character other than its own line ends, and no line that begins with `CLEAN` or `DRIFT` other than the detector's own |
| E02 | the same, `--json` | valid JSON; the label round-trips exactly |
| E03 | non-ASCII label, `PYTHONIOENCODING=ascii` | completes; no traceback |
| E04 | a refusal that quotes the offending input (D05 with a key holding an escape) | stderr holds no raw control character |

**F — what it does to the machine**

| id | setup | required |
|---|---|---|
| F01 | X5: `core.fsmonitor` set to a command that creates a marker file | marker absent after the run |
| F02 | `filter.x.clean` set to a command creating a marker, `.gitattributes` routing a modified file through it | marker absent; `working_tree_dirty` is `null` and the report says why |
| F03 | repository with a modified, stat-dirty tracked file | every file under the repository, `.git` included, is byte-identical before and after the run |
| F04 | static scan of the detector | imports nothing that opens a network connection; the only program it starts is `git` |

**G — stamp and determinism**

| id | required |
|---|---|
| G01 | two runs over the same repository print identical bytes (`--json` and text) |
| G02 | `stamp.detector_closure` is the first 16 hex of the SHA-256 of the detector file run |
| G03 | `working_tree_dirty` false on a clean tree, true after modifying a tracked file |

**H–K — the rest**

| id | required |
|---|---|
| H01 | `tests/fixture_label_only.py`, unchanged, passes against the detector under test |
| I01 | a command-line flag overrides the same setting in `.closure-drift.json` |
| I02 | with no flags, the settings in `.closure-drift.json` are the ones used |
| J01 | `pyproject.toml` with a dynamic version and `pkg/__init__.py` holding `__version__` → the label is found |
| K01 | an annotated tag and a lightweight tag are both resolved to their commits |

## 3. Negative controls — mutants of the detector

Each mutant is a copy with one change. The battery must exit 1 against it, with at least the
named proof red. A mutant whose change could not be applied counts as a **failed control**.

| id | the change | must turn red |
|---|---|---|
| M01 | `inconclusive` ends at exit 0 again | A03 |
| M02 | `ls-tree` without `-z` | C01 |
| M03 | a failing `git` call returns empty output instead of refusing | D14 |
| M04 | printed text is no longer escaped | E01 |
| M05 | the `core.fsmonitor` override is removed | F01 |
| M06 | submodule entries are skipped | C04 |
| M07 | the config file is not checked for being an object | D02 |
| M08 | points without a label are not counted | B01 |
| M09 | `drift` ends at exit 0 | A02 |
| M10 | the top-level guard is removed | D15 |

## 4. Adversarial campaign

Pre-registered and written by a reviewer who did not write the fixes, in
`PREREGISTRATION_ADVERSARIAL.md`.

## 5. Comparability with published results

The eight public repositories of the README's reference tables are measured with the 0.7.1
script and with the 0.8.0 script at the same commits. Required: every verdict field identical,
or each difference traced to X1/X10 (a path or submodule that 0.7.1 left out) and stated in the
README. Exit codes are expected to differ only where X3 applies.

## 6. Amendments

(none yet)

## 7. Added 2026-10-04, before any of it was written — the features of 0.8.0

Sections 0–6 above were written for a corrections-only release. The release now also carries
seven features. This section pre-registers them; nothing above is rewritten. The detector at
commit `35d093a` has none of them, so every proof below is red against it by construction.

**R — the report says which format it is**

| id | required |
|---|---|
| R01 | every JSON report, `no_publication_points` included, carries `"report_format": 2` |

**W — `--would-tag`: would tagging HEAD reuse a label that already names other code?**
It compares the label and closure of HEAD with the existing tag points. It answers about the
new tag only; drift already in the history is counted, not judged.

| id | setup | required |
|---|---|---|
| W01 | tags exist; the label at HEAD is at none of them | `would_be_clean`, exit 0 |
| W02 | the label at HEAD is at a tag whose closure differs | `would_drift`, exit 1, the report names that tag |
| W03 | the label at HEAD is at a tag with the same closure | `would_be_clean`, exit 0 |
| W04 | no tags at all | `would_be_clean`, exit 0 |
| W05 | HEAD declares no label | `no_label_at_head`, exit 2 |
| W06 | nothing at HEAD matches the closure globs | `empty_closure_at_head`, exit 2 |
| W07 | `--would-tag --at commits` | refusal, exit 2 |
| W08 | history already in drift under other labels; label at HEAD is new | `would_be_clean`, exit 0, `existing_drift_labels` = 1 |
| W09 | tracked file modified, not committed | the answer is the one for the commit; `working_tree_dirty` true; the text report says the commit was measured, not the working tree |

**T — `--tags GLOB`: which tags are publication points**

| id | setup | required |
|---|---|---|
| T01 | tags `rs-1`, `py-1`, `py-2`; `rs-1` and `py-1` share a label with different closures | default: `drift`; with `--tags 'py-*'`: `clean` |
| T02 | `--tags 'nothing-*'` | `no_publication_points`, exit 2, the message names the glob |
| T03 | `"tags": ["py-*"]` in the config file is honoured; `--tags` on the command line overrides it |
| T04 | the report carries `tag_globs` and `tags_filtered_out` |
| T05 | `--tags` with `--at commits` | refusal, exit 2 |

**S — `--strict`: `clean` only when every point scanned was compared**

| id | setup | required |
|---|---|---|
| S01 | the repository of B01 (2 of 4 tags without a label), `--strict` | `incomplete`, exit 2 |
| S02 | every tag labelled and non-empty, `--strict` | `clean`, exit 0 |
| S03 | drift, `--strict` | `drift`, exit 1 |
| S04 | 5 tags, `--max-commits 3 --strict` | `incomplete`, exit 2 |

**X — `--explain LABEL`: which paths differ**

| id | setup | required |
|---|---|---|
| X01 | one label, two closures: one file changed, one added, one removed | `explain` lists exactly those three paths under `changed`, `only_in_other`, `only_in_first` |
| X02 | `--explain` naming a label that covers one closure, or no label | refusal, exit 2 |
| X03 | the differing path holds a line break and an escape | the text report carries no raw control character |
| X04 | drift, without `--explain` | no path of any file inside the closure appears anywhere in the report, text or JSON |

**U — the closure is identified by all of its hash, and by an unambiguous encoding**
The 16-hex value of every earlier version stays in the report, unchanged, so published values
remain comparable. Identity is decided by a second value: SHA-256, all 64 hex, over records
`path NUL type SP object-id LF`.

| id | setup | required |
|---|---|---|
| U01 | drift | `closure_ids` maps every 16-hex closure in `drift` to a 64-hex value |
| U02 | two tags, one label: tag 1 holds `src/a` (blob X) and `src/b` (blob Y); tag 2 holds the single file `src/a<X>src/b` (blob Y). The earlier construction hashes the same bytes for both | `drift`, exit 1 |

**P — reading trees faster gives the same closure**

| id | setup | required |
|---|---|---|
| P01 | a repository with nested folders, a symbolic link, an executable file, a submodule pointer, a non-ASCII name; every commit | the entries the detector reads equal, in order, those of `git ls-tree -r -z`, parsed independently in the battery |
| P02 | a repository created with `--object-format=sha256` | A01 and A02 hold; `not_run` where git cannot create one |

**G — badge**

| id | required |
|---|---|
| G04 | `--badge` prints exactly one line of Markdown naming the verdict and the 12-hex HEAD measured, and nothing else; exit code as for the verdict |

**Mutants added**

| id | the change | must turn red |
|---|---|---|
| M11 | `--would-tag` no longer compares closures | W02 |
| M12 | `--tags` is accepted and ignored | T01 |
| M13 | `--strict` is accepted and ignored | S01 |
| M14 | identity is decided by the 16-hex value again | U02 |
| M15 | `explain` is filled in without being asked | X04 |

Exit codes with the new verdicts: `would_be_clean` 0; `would_drift` 1; `incomplete`,
`no_label_at_head`, `empty_closure_at_head` 2. The closed set of §1 is unchanged: 0 is a pass,
1 is drift, 2 is no determination.

### Amendments to §2–§3 and §7, 2026-10-04 (after the adversarial campaign, before the features were run)

- **D17 added.** The adversarial campaign found that a `version_regex` written never to finish,
  in the measured repository's own config file, hangs the detector (its case EC18). Required: a
  named refusal, exit 2, well inside 90 seconds.
- **M02 and M03 re-expressed, same intent.** The detector no longer calls `ls-tree`; it reads
  tree objects through one `git cat-file --batch`. M02 ("paths that are not plain ASCII leave
  the closure") is now a mutant that drops non-ASCII paths; M03 ("a failing git read is taken
  as an answer") is now a mutant that returns a made-up object where `cat-file` reported none.
  The proofs they must turn red are unchanged (C01, D14).
- **F04 widened by one program.** The detector now also starts itself, to match a version
  pattern that is not one of its own under a time limit. F04 requires that the only programs
  started are `git` and the detector's own file with `--match-on-stdin`.
- **K02 added, 2026-10-04, after the detector was frozen.** The JSON report is documented as a
  contract in `docs/REPORT.md`; K02 checks that each kind of report carries the fields listed
  there, that every verdict is in the closed set and leaves at its documented exit code, and that
  a refusal leaves standard output empty. It tests the detector as it already was: no code changed
  for it, and it could have been red.

