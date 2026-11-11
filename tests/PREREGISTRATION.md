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


## 8. Added 2026-10-04, before any of it was written — what turns 0.8.0 into 0.9.0

The release prepared as 0.8.0 was never tagged or deposited; it is the base of 0.9.0. This section
pre-registers what 0.9.0 adds. The detector at commit `e56e71c` has none of it, so every proof
below is red against it by construction. `report_format` stays `2`: fields are only added.

**CMP — `--compare A B`: two references, side by side.** It looks at exactly two commits and
ignores publication points. It always lists the paths, because asking for the comparison is
asking for them.

| id | setup | required |
|---|---|---|
| CMP01 | two tags, one label, closures differ by one changed, one added and one removed file | verdict `differs_under_one_label`, exit 1; `changed`, `only_in_a`, `only_in_b` list exactly those paths |
| CMP02 | two tags, two labels, closures differ | `differs_under_two_labels`, exit 0 |
| CMP03 | two tags whose closures are the same | `identical`, exit 0, the three lists empty |
| CMP04 | a reference that does not exist | refusal, exit 2, naming the reference |
| CMP05 | one of the two declares no label | `not_comparable`, exit 2; the paths are still listed |
| CMP06 | a differing path holding a line break and an escape | no raw control character in the text report; in JSON the path round-trips |
| CMP07 | `--compare` with `--would-tag`, with `--explain`, with `--at commits` | refusal, exit 2, each |

**DG — `--diagnose`: what to paste into a bug report.**

| id | setup | required |
|---|---|---|
| DG01 | drift repository, `--diagnose` | the text report opens with a block naming the detector version, its 16-hex hash, the Python version and the git version; that block holds no version label, no path inside the closure and no path of the repository; the verdict and exit code are those of the same run without `--diagnose` |
| DG02 | `--diagnose --json` | the report carries a `diagnostics` object with `detector_version`, `detector_closure`, `python`, `git`, `platform`, `options`, `repository` |
| DG03 | `--diagnose` on a directory that is not a repository | the block is printed, then the refusal; exit 2 |

**VER — the detector knows its own version**

| id | required |
|---|---|
| VER01 | `--version` prints `closure_drift` and the value of `__version__` in the file, exit 0, and nothing else |

**TV — a version that comes from the tag is said to come from the tag**

| id | setup | required |
|---|---|---|
| TV01 | `pyproject.toml` naming `setuptools_scm`, no static version anywhere | refusal, exit 2, whose text says the version is derived from the tag at build time and names the tool found |
| TV02 | no version file of any kind | the refusal is the earlier one ("could not find a version label"), not the new one |

**TF — tag families are pointed out, not guessed at**

| id | setup | required |
|---|---|---|
| TF01 | tags `rs-1` and `py-1` share a label with different closures | `drift`; the report carries `tag_families` naming both `rs-` and `py-`, and the text suggests `--tags` |
| TF02 | drift between `v1` and `v2`, one family | no `tag_families`, no suggestion |

**Mutants added**

| id | the change | must turn red |
|---|---|---|
| M16 | `--compare` reports no differing path | CMP01 |
| M17 | the diagnostics block prints the repository path | DG01 |
| M18 | the tag-derived cause is not named | TV01 |
| M19 | `--compare` of one label with two closures leaves at exit 0 | CMP01 |

### Amendments of 2026-10-04, after the adversarial extension for 0.9.0

- **EX01, EX02 and M20 added.** The extension found that the excluded folders are excluded only
  below the top level: `**/tests/**` did not match a `tests/` folder at the root of the
  repository, so its files were inside the closure whenever an include glob matched them (the
  default `*.py` does). This predates 0.9.0 and contradicts the statement that those folders are
  never part of a closure. Required: a change confined to a root-level `tests/`, `docs/` or
  `*.md` is not seen (EX01), exactly as it is not seen one level down (EX02). M20 removes the
  correction and must turn EX01 red.
- **What this does to comparability, measured before the correction was adopted**: over the seven
  reference repositories the verdict, the number of labels, the labels in drift, the worst label,
  the points and the churn are identical with and without it. The 16-hex closure VALUES change in
  the three repositories in drift, because files that were wrongly inside the closure leave it.
  C05 still holds: where no excluded folder sits at the root, the closure is the earlier value.
- **`--would-tag` looks at every tag**, not at the most recent `--max-commits`; a tag with the
  same label and an empty closure counts as a collision; a `--tags` glob that leaves no tag is
  `no_publication_points`. Each was a case of the extension that passed a real collision.
- **Two controls failed on the first full run of the 20 mutants, and both were the controls' own
  fault.** M18 no longer applied (the line it changes had been rewritten). M03 applied and was not
  caught: it made a failed object read return garbage, and the tree validation added the same day
  refused the garbage, so D14 stayed green for a different reason. M03 now returns an EMPTY object
  — a tag read as holding no files — and D14 additionally requires that no report at all is
  produced. A control that passes for the wrong reason is the case these controls exist for.


## 9. Added 2026-10-04, before any of it was written — finding the label where projects keep it

The first run of the study (`tools/study/`, run 1) said more about the detector than about the
projects: of 100 repositories, 34 were refused for want of a version label, and in 7 of the 21
`drift` results the label read was a constant that is not the released version. Three causes,
each seen in named repositories of that run, and what is required instead. The detector at
commit `HEAD` of this file's addition has none of it.

**PT — the source of the label is resolved at each publication point, not once at HEAD.**
A project moves its version from `setup.py` to `__init__.py` to `pyproject.toml` over the years;
run 1 compared 11 of 71 tags of `click` and 12 of 162 of `requests` for that reason.

| id | setup | required |
|---|---|---|
| PT01 | tag 1 declares the version in `setup.py`, tag 2 in `pkg/__init__.py`, tag 3 in `pyproject.toml`; three labels, three closures | `clean`, 3 points compared, `label_sources` lists the three |
| PT02 | the same history, tags 1 and 3 declaring the same label with different code | `drift` |
| PT03 | `--version-file` given | that file is used at every point, as before; no resolution |

**TL — when the version is derived from the tag, the label is the tag.**
With `setuptools_scm`, `hatch-vcs`, `versioneer` and the like, the released version is computed
from the tag name. The label is then the tag name without a leading `v`.

| id | setup | required |
|---|---|---|
| TL01 | `pyproject.toml` names `setuptools_scm`; tags `v1.0`, `v1.1`; a file elsewhere holds a constant `__version__ = "unknown"` | `clean`, labels `1.0` and `1.1`, `label_sources` = tag; the constant is not read |
| TL02 | the same, plus a tag `1.0` on a commit with different code | `drift`: `v1.0` and `1.0` both build version 1.0 |
| TL03 | tag-derived, `--at commits` | refusal, exit 2: there is no tag to read the label from |
| TL04 | tag-derived, `--would-tag` | `no_label_at_head`, exit 2, saying the version will be the tag |
| TL05 | the tool is named only in a comment | not treated as tag-derived |

**VP — a declared pointer to the version is followed.**

| id | declaration | label read from |
|---|---|---|
| VP01 | `[tool.hatch.version]` `path = 'pkg/version.py'` | that file |
| VP02 | `version = {attr = "pkg.__version__"}` under `[tool.setuptools.dynamic]` | `pkg/__init__.py` or `src/pkg/__init__.py` |
| VP03 | `version = attr: pkg.__version__` in `setup.cfg` | the same |
| VP04 | `version = {file = "VERSION.txt"}` / `version = file: VERSION.txt` | that file |
| VP05 | `flit_core` backend, `dynamic = ["version"]`, project `name = "pkg"` | `pkg/__init__.py`, `src/pkg/__init__.py` or `pkg.py` |
| VP06 | `setup.py` with `version=pkg.__version__` or `version=mod.VERSION` | the module named, wherever it is shallowest |
| VP07 | `setup.py` with a module-level `VERSION = '1.2.3'` and `version=VERSION` | `setup.py` |
| VP08 | a vendored package deeper in the tree also defines `__version__` | the shallowest candidate wins; the vendored one is not read |
| VP09 | none of the above and no version file | the refusal "could not find a version label", as before |

Each VP proof builds two tags with two versions and two closures and requires `clean` with both
labels read; VP08 additionally changes the vendored constant and requires that nothing moves.

**Mutants added**

| id | the change | must turn red |
|---|---|---|
| M21 | the source is resolved once, at HEAD | PT01 |
| M22 | a tag-derived project falls through to the constants in the tree | TL01 |
| M23 | the leading `v` is not removed from a tag label | TL02 |
| M24 | declared pointers are not followed | VP01 |

**What this does to earlier results, stated before measuring it.** Resolving the source at each
point compares more points. On the seven reference repositories the verdicts may change where
tags that 0.7.1 could not read turn out to share a label. Whatever comes out is reported; with
`--version-file` fixed to what 0.7.1 read, the counts must still equal 0.7.1's.

### Amendments to §8, made with §9

- **TV01 is superseded by TL01.** §8 required a refusal naming the tag-derived tool; §9 makes that
  project measurable, with the tag as the label. TV01 now requires the report to say the label
  came from the tag.
- **M18 is re-expressed.** It removed the naming of the tag-derived cause, which no longer exists
  as a refusal. It now removes the stripping of comments, and must turn TL05 red.


### Amendment to §9, 2026-10-04 — a label must be a version, written before the change

A preview of study run 2, made with the first implementation of §9 and not published as a
result, showed labels covering dozens of tags that are not versions at all: `%(version)s` and
`{}.{}.{}` (format templates in `setup.py`, numpy), ` (%s)` (Pillow), `.` (the separator of
`'.'.join(...)`, tqdm), `unknown` (a fallback, setuptools), `0.6c5` (the `version=` argument of
another call in `setup.py`, pandas), `0.0.0` (a dynamic-version placeholder, opentelemetry).
Required instead:

| id | setup | required |
|---|---|---|
| PL01 | a source yields `%(version)s`, `{}.{}.{}`, `%s`, `unknown`, `.` or `0.0.0` | that source is not a label source at that point; resolution goes on to the next rule; if none remains the point has no label |
| PL02 | `__version__ = '.'.join(map(str, version_info))` in the shallowest module, and a literal version in another | the literal one is read |
| PL03 | `setup.py` calls `use_setuptools(version="0.6c5")` and then `setup(version="1.2.3")` | the label is `1.2.3`, at two tags with two versions |
| PL04 | `setup.py` that is not valid Python 3 (a `print` statement) with a plain `version="1.2.3"` | the label is still read |
| PL05 | `--version-file` and `--version-regex` given | the label is whatever the pattern captures, as before; no plausibility rule is applied to an explicit source |

Mutants: M25 removes the plausibility rule and must turn PL01 red; M26 reads `version=` from any
call in `setup.py` and must turn PL03 red.

### Amendment, 2026-10-05 — 0.9.1

Mutant M20 removed a line of `matches` that 0.9.1 changes (`fnmatch.fnmatch` → `fnmatch.fnmatchcase`,
`tests/PREREGISTRATION_PROPERTIES.md`). Against 0.9.1 it did not apply and was reported not caught.
Its anchor now names the new text; the proof it must turn red (EX01) is unchanged.

## 10. Added 2026-10-05, before any of it was written — the four open failures of 0.9.1

`docs/FAILURES.md` O1–O4, found by the benchmark of ten large repositories
(`tools/benchmark/READING.md`). The detector at the commit adding this section is 0.9.1, sha256
`89b5349928eba22b0394d01940ed3d4aa989d6820f48fdddf189ad521689c51c`. What is not here is not
changed. The release is 0.10.0: two of the changes can turn an exit 0 or 1 of 0.9.1 into 2.

**CV — `clean` must rest on most of what was scanned (O1).**
On `Azure/azure-sdk-for-python` 0.9.1 answered `clean`, exit 0, with 9 of 5,508 tags compared.
Rule: a point is *uncompared* when it has no label or an empty closure. `clean` requires at least
as many compared points as uncompared ones; otherwise the verdict is `incomplete`, exit 2.
`drift` is unaffected: a collision found is a fact whatever the coverage. `--strict` keeps its
meaning (every point compared). Measured before the change, from the stored reports of study
run 2: 4 of its 63 `clean` have fewer compared than uncompared points (`coveragepy`, `scipy`,
`tqdm`, `idna`) and would be `incomplete`.

| id | setup | required |
|---|---|---|
| CV01 | 2 labelled tags with distinct labels, 3 tags without a label | `incomplete`, exit 2 |
| CV02 | 3 labelled tags with distinct labels, 3 without | `clean`, exit 0 (equal counts) |
| CV03 | 2 labelled tags under one label with different code, 5 without | `drift`, exit 1 |
| CV04 | 2 labelled tags, 3 tags whose closure is empty | `incomplete`, exit 2 |
| CV05 | the report of CV01 | carries `publication_points_compared` 2 and the uncompared counts; the text names the rule |

**AG — a version file that no tag confirms is not believed (O2).**
On `git/git` 0.9.1 read `0.1.0` from the root `Cargo.toml` of a helper crate and answered `drift`;
on `DefinitelyTyped` it read `0.0.3` from a private `package.json` and answered `would_drift`.
In both, no tag named for a version agrees with what the file declares.
Rule, for a source found by the rules only (never one given with `--version-file`): at each tag
whose name carries a version, the file's label *agrees* when the leading run of numbers of both
is the same after trailing zeros are dropped (`v2.52.0-rc0` and `2.52` agree; `1.0` and `1.0.0`
agree). A source that was read at one or more such tags and agrees at none is *contradicted*:
its points count as without label, a new field `points_label_contradicted` counts them, and the
source is named. Under `--would-tag`, a label at HEAD from a contradicted source is not believed:
`no_label_at_head`, exit 2, with the source named. A tag whose name carries no version
(`release-candidate`, `nightly`) takes no part.

| id | setup | required |
|---|---|---|
| AG01 | tags `v2.1.0`, `v2.2.0`; a root `Cargo.toml` declares `0.1.0` at both, different code | not `drift`; `no_labels`, exit 2; `points_label_contradicted` 2; the source is named |
| AG02 | tags `v1.0`, `v1.1`; `pyproject.toml` declares `1.0.0`, then `1.1.0` | `clean` (agreement after trailing zeros) |
| AG03 | tags `v1.0.0`, `v1.1.0`, `v1.2.0`; the file declares `1.0.0`, `1.1.0`, `1.1.0` with different code at the last two | `drift`: one disagreement among agreements is the finding, not a contradiction |
| AG04 | as AG01, with `--version-file Cargo.toml` | `drift`, exit 1: a declared source is not second-guessed |
| AG05 | tags `nightly`, `stable` only; the file declares `0.1.0` at both with different code | `drift`: no tag carries a version, so nothing contradicts the file |
| AG06 | as AG01, `--would-tag` at a HEAD declaring `0.1.0` | `no_label_at_head`, exit 2, the source named |
| AG07 | tag `v2.52.0-rc0`, file `2.52.0`; tag `v2.53.0`, file `2.53.0` | `clean` |

**NG — a version spread over several places in one file (O3).**
Six of the ten large repositories keep their version where the rules do not look, and three of
them (`linux`, `node`, `llvm`) spread it over several lines, which one capture group cannot
assemble. Rule: when `--version-regex` has **named** groups, the label is their non-empty values
in order, joined by `.`; a value starting with `-` or `+` is attached without the dot. A pattern
without named groups keeps its meaning (group 1), so no existing configuration changes. The
refusal for want of a label says where to look, and that a project whose version is the tag has
nothing to measure here.

| id | setup | required |
|---|---|---|
| NG01 | a `Makefile` with `VERSION = 6`, `PATCHLEVEL = 1`, `SUBLEVEL = 0`; the pattern names three groups | label `6.1.0` |
| NG02 | the same with `EXTRAVERSION = -rc1` as a fourth named group | label `6.1.0-rc1` |
| NG03 | a fourth named group that matches empty | label `6.1.0` |
| NG04 | a pattern with two unnamed groups | label is group 1, as in 0.9.1 |
| NG05 | the refusal for want of a label | names `--version-file` / `--version-regex`, the named-group form, and the tag case |

**MM — memory does not grow with history (O4).**
Every tag of `torvalds/linux` took 3.4 GB under 0.9.1, because every tree object read is kept.
Rule: the cache of tree objects holds at most a fixed number of entries, oldest use evicted.
No output may change.

| id | setup | required |
|---|---|---|
| MM01 | a repository of 60 tags whose trees all differ, with the cache bound set to 50 entries through the environment variable `CLOSURE_DRIFT_TREE_CACHE` | the same report, byte for byte, as with the default bound |
| MM02 | the same, bound 1 | the same report |

Required beyond the proofs:

- **Mutants** M27–M33, one per rule: CV rule removed (CV01), CV counted on scanned instead of
  uncompared (CV02), AG applied to a declared source (AG04), AG agreement on text instead of
  numbers (AG02), AG with a one-agreement threshold (AG03), NG joined without regard to `-`
  (NG02), LRU that evicts the entry just read (MM01 — a wrong entry must change a report).
- **All existing batteries** as before; the property suite after the oracle's specification is
  amended for CV and NG by its author.
- **An adversarial pass** on the four rules by a reviewer who did not write them, committed as
  delivered before any fix.
- **The study, run 3**: same selection, same rule, detector 0.10.0, run on GitHub's runners and
  kept beside runs 1 and 2. Expected from the stored run-2 reports: the 4 above move from `clean`
  to `incomplete`; whatever else moves is reported, not explained away.
- **The benchmark, run 2**: same ten, same protocol, detector 0.10.0, plus a run per repository
  with a declared version file where one exists, written in `docs/LABELS.md` before it is run.
  Required: every tag of `linux` under 1.5 GB peak; no run more than 1.5× slower than in run 1.
  `git/git` and `DefinitelyTyped` no longer answer `drift` or `would_drift`; `Azure` no longer
  `clean`.

Not in scope: O5 (the refusal comes after the scan), O6 (folder exclusions), O7, O8.

### Amendment to §10, 2026-10-05 — after the first run of the existing battery, before any new proof

Two proofs of 0.9.1 went red under AG as written:

- **J01**: tags `v1` and `v2`, versions `1.2.3` and `1.2.4`. Read as "the same leading numbers",
  `v1` does not agree with `1.2.3`, so the source was contradicted. A tag that names a major
  version only is common. **AG now reads: a tag agrees when its numbers, trailing zeros dropped,
  are the beginning of the file's numbers, trailing zeros dropped.** `v1` agrees with `1.2.3`;
  `v2.52` does not agree with `2.0.0` (the file is not allowed to be the shorter one, or a constant
  `2.0.0` would agree with every `v2.x`); `v1.0` agrees with `1.0.0`. AG01–AG07 are unchanged.
- **DG01**: tags `v1`, `v2` with label `7.7.7-label`. Under AG this repository is correctly no
  longer in drift — no tag agrees with the file — and the proof hard-codes exit 1. Its subject is
  the diagnostics block, not the label rule: the fixture's label becomes `1.7.7-label`, which `v1`
  agrees with. Nothing it checks is weakened.

### Amendment 2 to §10, 2026-10-05 — after adversarial extension 3, before any change to the code

Extension 3 (`tests/PREREGISTRATION_ADVERSARIAL.md`, committed as delivered) found that AG as
written **hides the failure this tool exists to find**: dropping the points of a contradicted
source removes the collisions they hold. In ZA10 that left a `clean`, exit 0, over a real
collision. A file that does not track the tags is what drift looks like, so "agrees with no tag"
also rejected textbook drift (ZA03, ZA11, ZX07). The rules are rewritten; nothing below drops a
point.

**AG, as amended.**
1. A tag *carries a version* when its name, after an optional prefix that starts with a letter
   and ends in `-`, `_` or `/`, and an optional `v`, starts with numbers separated by dots. The
   numbers are read as text, leading zeros dropped (no conversion to integers: ZA05). `2024-01-05`
   carries `2024` (the dashes end the run; ZA01).
2. At such a tag the file's label *agrees* when its first number equals the tag's first number.
   Tag-before-bump inside a major version agrees (ZA03); `0.1.0` against `v2.52` does not.
3. A source found by the rules is *contradicted* when, over the tags scanned, it disagrees at more
   tags than it agrees (ZA04: one coincidental agreement against three disagreements).
4. **A contradicted source decides nothing: the verdict is `incomplete`, exit 2**, the source is
   named in `contradicted_sources`, and every count stays as measured. Under `--would-tag`, a label
   at HEAD from a contradicted source is `no_label_at_head`, exit 2. Under `--compare`, two tags
   whose labels come from the rules and both disagree with their tag are `not_comparable`, exit 2
   (ZX02).
5. A `package.json` with `"private": true` is never a source: npm refuses to publish it, so its
   version names no release (DefinitelyTyped).
6. A source given with `--version-file` is never second-guessed, but a label read from it must
   contain a digit; otherwise the point has no label (ZN01: a pattern capturing a quote gave two
   different labels `"` and `'` and a `clean`, exit 0).

Proofs: AG01 now requires `incomplete`, exit 2, `contradicted_sources` `["Cargo.toml"]` and
`points_label_contradicted` 2. AG02–AG07 stand. New: AG08 (ZA10's two eras → not `clean`), AG09
(ZA11 → `drift`), AG10 (private `package.json` → not read), AG11 (a declared pattern capturing a
quote → no label). Mutants: M29 (rule applied to a declared source → AG04), M30 (agreement on text →
AG02), M31 (contradicted when any tag disagrees → AG03), M34 (contradiction drops the points
instead of refusing → AG08), M35 (private `package.json` read → AG10).

**NG, as amended.** ZN02: a pattern of 0.9.1 that already named a group changed meaning. Only
groups named `part` followed by digits (`part1`, `part2`, …) are joined; any other pattern keeps
group 1. NG01–NG03 use those names.

**MM, as amended.** ZM05: under a small bound, a parent tree evicted while its children are read
was read again after each child. `entries` keeps the list it is walking. ZM06: the cache of version
files grew with history; it is bounded too (32 MiB). MM03 stands.

**Not changed, recorded as limits:** `--at commits` has no tag to check a source against (ZX03);
build-number tags such as `release-41` read as versions and can contradict a correct file, which
now gives exit 2, not a wrong answer (ZA02). LR02 and LR03 of the earlier campaign required the
automatic run to equal the `--version-file` run on a fixture whose tags `v1`, `v2` disagree with
`0.1.0`, `0.2.0`; by AG that is now a refusal, by design, and they are marked superseded.

### Amendment 3 to §10, 2026-10-05 — after running the campaign against amendment 2

Amendment 2, run against the whole campaign, broke cases that 0.9.1 passed:

- **LR01, LR04, LR06**: tags `v1`, `v2`, `v3` over versions `1.0`, `1.0`, `2.0` — real drift on
  `1.0`. Under "disagrees at more tags than it agrees" (1 against 2) the file was refused. **A
  source is contradicted only when it agrees at no tag carrying a version.** ZA04 (one coincidental
  agreement keeps a helper file believed) becomes a recorded limit.
- **ZV05**: a collision under a believed source, beside a contradicted one, became `incomplete`.
  **Order of the verdict**: `drift` over the believed sources first; then, if any source is
  contradicted, `incomplete`; then the rest. A contradicted source's points are counted in
  `points_label_contradicted` and in `points_without_label`, and decide nothing. ZA10 stays not
  `clean`: its only collision is under the contradicted source.
- **OI07, XP01, XP05, TR01**: "a declared label must contain a digit" turned labels such as
  `clean` or `--json` into no label. **A declared label must contain a letter or a digit**; a label
  of punctuation only (ZN01's quote) is no label.

Proof AG01 requires `incomplete` as in amendment 2, with the counts of this amendment
(`publication_points_compared` 0, `points_without_label` 2); `label_sources` leaves out a
contradicted source, which `contradicted_sources` names (ZX04). Mutant M31 becomes "contradicted when any tag
disagrees" against a new proof AG12 (tag before bump across a major version: `v1.0` declares `0.9.0`,
`v1.1` and `v1.1.1` declare `1.0.0` with different code → `drift`) and M34 "a contradicted source does not prevent `clean`" (AG08).

Cases of extension 3 whose required outcome was written against the first form of AG or NG, and
that the amendments answer differently by design, are listed with their new requirement in
`tests/PREREGISTRATION_ADVERSARIAL.md`, "Amendment by the maintainer after extension 3".

### Amendment 4 to §10, 2026-10-05 — after benchmark run 2

The refusal for want of a label (NG05) still showed the named-group example with the names `a`
and `b`, which amendment 2 stopped joining: followed as printed, it reads `6`, not `6.1`. NG05
only checked for `(?P<`. The example now uses `part1`, `part2`; NG05 requires `(?P<part1>`. The same
mistake was in the benchmark's recipes (`tools/benchmark/recipes.json`), found in their results.
Only the text of that refusal changes in the detector. Study run 3 and benchmark run 2 were measured
with the script before this change (sha256 `08ceb754…`); no measurement reads that message.

### Amendment 5 to §10, 2026-10-05 — MM did not meet its requirement

Benchmark run 2 measured every tag of `torvalds/linux` at 3.3 GB with 0.10.0, the same as 0.9.1:
the requirement (under 1.5 GB) was **not met**, and that result stays recorded. Measured since, on
a clone of CPython, the two processes apart: the detector's own heap held about 280 MB, nearly all
of it the tree cache at its bound of 1,000,000 entries, and `git cat-file` about 375 MB, which is
git mapping the repository's pack files into memory — 6.5 GB of them on the kernel. The bound
contained the cache but was set too high to matter, and the larger part was never the detector's.

The change, written before it is made:

1. Every git call adds `-c core.packedGitWindowSize=32m -c core.packedGitLimit=256m`. Measured on
   CPython: `git cat-file` 375 → 217 MB, 17 → 14 s, the same report.
2. The default bound of the tree cache becomes 250,000 entries.

Required: benchmark B3 of `torvalds/linux` under 1.5 GB peak for the whole process tree, no more
than 1.5 times slower than 0.9.1 on the same clone; every suite as before; the same reports as the
script measured in study run 3 and benchmark run 2, apart from the stamp, on the six reference
repositories and the 60 seeds of the property suite.

### Note, 2026-10-06 — wording only

Where §10 and its amendments say "the benchmark of 0.9.1", run 1 of the benchmark was measured with
0.9.0; 0.9.1 gives the same reports there (it differs only on Windows). Nothing else changes.

## 11. Added 2026-10-06, before any of it was written — what 1.0 has to meet

1.0 adds no capability to impress. It is the release that a reviewer who examines it cannot
discredit. Every line below is checked by a command or a file; a line that cannot be met is
written down as scope, with the reason, or 1.0 does not ship.

| id | requirement | how it is checked |
|---|---|---|
| R1 | No proof red, every mutant caught, no loose adversarial case outside the closed known list, every property green — on Linux, macOS and Windows | `tests/RECORD.md`, CI run named there |
| R2 | The same on every Python the package declares: 3.9, 3.10, 3.11, 3.12, 3.13, 3.14 | CI matrix; `pyproject.toml` classifiers equal to it |
| R3 | A regression corpus: the 100 repositories of the study, each pinned to a recorded HEAD and set of tags; the release must reproduce the recorded classification of every repository whose snapshot is intact | `tools/regression/`; a repository whose upstream moved or deleted a recorded tag is reported, by name, as not checkable |
| R4 | No known correctness defect left unresolved: every open item of `docs/FAILURES.md` that can produce a wrong `clean` or `drift` is fixed, or declared in `SCOPE.md` with the condition under which it applies and the way to avoid it | `docs/FAILURES.md` against `SCOPE.md` |
| R5 | Monorepos: components declared in `.closure-drift.json`, each with its own tags, version file and closure, one verdict each. Declared, never inferred | proofs CP*, mutants, adversarial pass |
| R6 | Scale, measured by a recurring job: every tag of `torvalds/linux`, `llvm/llvm-project`, `python/cpython`, `rust-lang/rust`, `nodejs/node`, with time, peak memory of the whole process tree, tags scanned, compared, without label, and objects read; the kernel under 1 GB | `.github/workflows/benchmark.yml`, scheduled |
| R7 | Every quantitative claim of the public pages traceable to a file of the repository; no "production-grade", "secure", "enterprise" or similar without a measurable definition | an independent review of the whole repository, committed as delivered |
| R8 | Reproducibility: `reproduce.sh` runs every suite; the release's script hash in `DEPOSIT.sha256` matches the Zenodo record | `tools/verify_deposit.py --from-zenodo` |

Not required, and why: incremental analysis (every tag of the kernel takes about two minutes;
nothing measured asks for it, and it would add state); inferring components (declaring them is
what R5 asks for); a guarantee for the label rules without `--version-file` (they refuse on
contradiction, and are best effort otherwise — R4 writes that down).

The proofs, mutants and cases for R3–R6 are written in sections 12 onward, each before its code.

## 12. Added 2026-10-06, before any of it was written — the regression corpus (R3)

The 100 repositories of the study become a regression corpus. The study answers "what is out
there"; the corpus answers "does this release still say what the last one said, on the same
bytes".

**Snapshot.** For each repository of `tools/study/selection.tsv`: a full bare clone; its HEAD
commit; every tag with the object it points to (`for-each-ref refs/tags`); and the report of
the detector that took the snapshot, at its defaults. Stored as `tools/regression/corpus/<repo>.json`
with the detector's sha256. Taken once, on GitHub's runners, with 0.10.0.

**Check.** Clone again; if the recorded HEAD commit is missing, or a recorded tag is missing or
points elsewhere, the repository is *not checkable* and is reported by name with the cause. Tags
added since are deleted from the clone; HEAD is set to the recorded commit. Then the detector runs
at its defaults and these fields are compared with the snapshot: `verdict`, exit code, `labels`,
`labels_covering_multiple_closures`, `publication_points_scanned`, `publication_points_compared`,
`points_without_label`, `points_with_empty_closure`, `points_label_contradicted`, and, for every
label in drift, the set of full closure ids.

**Rule for a release.** Every checkable repository matches, or the difference is one this
pre-registration predicted for that release, by repository and field, before the check ran. An
unpredicted difference is a regression; the release does not ship with it. After a release whose
predicted differences were confirmed, the snapshot's expected values are updated by a separate,
named commit.

Required of the check itself, on its first run against the detector that took the snapshot: every
checkable repository matches. Required of its controls: run with 0.9.1, `coveragepy`, `idna`,
`scipy` and `tqdm` must be reported as differing (`clean` against `incomplete`) and nothing else
in those fields — the four that study run 3 found.

### Note to §12, 2026-10-06, before the first snapshot

A field that the older of two reports does not carry is not compared (0.9.1 has no
`points_label_contradicted`). Nothing else changes.

## 13. Added 2026-10-06, before any of it was written — closing the open correctness items (R4)

Every open row of `docs/FAILURES.md` that can produce a wrong `clean` or `drift`:

| row | decision | why |
|---|---|---|
| O6 — file-name exclusions also matched folders (`src/x_test.d/real.py` left out by `**/*_test.*`) | **fixed** | a closure must not lose code because of a folder's name |
| O2a — a wrong version file believed when one tag agrees by chance | **declared** in `SCOPE.md` | the agreement rule is evidence, not proof; every stronger rule tried refused real drift (amendment 3 to §10). A gate passes `--version-file`, which is never second-guessed |
| O2b — build-number tags read as versions can refuse a correct file | **declared** | the answer is exit 2, never a wrong 0 or 1 |
| O2c — `--at commits` has no tag to check a file against | **declared** | the same as O2a, for that mode |
| O10 — a tag that was never released counts as a publication point | **declared** | which tags were released is in a package index, not in the repository; this tool reads only the repository. `--tags` selects the tags that are releases |
| O8 — no test asserts that `setup.py` is never run | **proof added** | |

**O6, the rule.** An exclusion whose pattern is `**/` followed by a name with no `/`
(`**/*_test.*`, `**/*.test.*`, `**/*.md`) is matched against the file name only. Folder exclusions
(`**/tests/**`, `**/docs/**`, …) are unchanged. `--closure` globs are unchanged.

| id | setup | required |
|---|---|---|
| EX10 | two tags, one label; only `src/x_test.d/real.py` changes | `drift` (in 0.10.0: not compared) |
| EX11 | the same with `src/a.test.utils/core.js` | `drift` |
| EX12 | the same with `pkg/notes.md/run.py` | `drift` |
| EX13 | only `src/foo_test.py` changes | not `drift`: still excluded |
| SP01 | a `setup.py` that writes a marker file when run, and declares the version | the marker never appears; positive control: `python setup.py --version` creates it |

Mutants: M36 (O6 reverted → EX10), M37 (the name rule applied to folder patterns too, so
`**/tests/**` stops excluding → an existing proof of root-level `tests/` exclusion).

Effect predicted on the regression corpus (§12): **no repository changes**. Any that does is named,
with the path that moved, and decides whether this prediction was wrong.

The oracle's specification is amended for O6 by its author before the comparison.

## 14. Added 2026-10-06, before any of it was written — components declared (R5)

A monorepo releases several artefacts, each with its own tags, version file and code. One
verdict over all of them mixes families (`polars`, `lodash`, the SDK monorepos of the benchmark).
The project says which components it has; the tool never guesses them.

```json
{"components": {
  "python": {"tags": ["py-*"], "version_file": "py/pyproject.toml", "closure": ["py/**"]},
  "rust":   {"tags": ["rs-*"], "version_file": "rs/Cargo.toml", "closure": ["rs/**"]}
}}
```

- Each component has `tags` (required, a non-empty list of globs) and may have `version_file`,
  `version_regex` and `closure`, with the meaning they have at the top level. Anything else, an
  empty `components`, or a component without `tags`, is a refusal. `components` cannot be combined
  with top-level `tags`, `version_file`, `version_regex` or `closure`.
- Without `--component`, every component is measured and the answer is one report per component
  plus one verdict: `drift` (exit 1) if any component is in drift; `clean` (exit 0) if every one
  is clean; otherwise `incomplete` (exit 2). `--json` gives
  `{"mode": "components", "verdict", "components": {name: report}}`.
- `--component NAME` measures that component only and prints its ordinary report, with
  `"component": NAME`. An unknown name is a refusal.
- `--would-tag`, `--compare` and `--explain` answer about one component: without `--component` they
  are refused. `--tags`, `--closure`, `--version-file` and `--version-regex` on the command line,
  with `components` in the file and no `--component`, are refused as ambiguous.
- A tag that matches the globs of two components is measured in both. Nothing is exclusive unless
  the globs make it so.

| id | setup | required |
|---|---|---|
| CM01 | `py-*` tags clean, `rs-*` tags in drift | `drift`, exit 1; `components.python.verdict` `clean`, `components.rust.verdict` `drift` |
| CM02 | both clean | `clean`, exit 0 |
| CM03 | one clean, one where no version is found | `incomplete`, exit 2 |
| CM04 | `--component rust` | the rust report only, `drift`, exit 1, `"component": "rust"` |
| CM05 | `--component nope` | refusal, exit 2, naming the components that exist |
| CM06 | `--would-tag` without `--component`; then with `--component rust` | refusal; then the would-tag answer for rust |
| CM07 | a component with an unknown key; `components` empty; a component without `tags`; `components` beside a top-level `tags` | four refusals |
| CM08 | `--tags 'x*'` on the command line, `components` in the file, no `--component` | refusal |
| CM09 | the text report of CM01 | names each component with its verdict |
| CM10 | one tag matching both components' globs | counted in both |

Mutants: M38 (a component without a version counts as clean → CM03), M39 (`--component` ignored →
CM04), M40 (`--would-tag` allowed without `--component` → CM06). An adversarial pass on components
by a reviewer who did not write them, committed as delivered before any fix.

## 15. Added 2026-10-06, before any of it was written — the benchmark as a recurring job (R6)

The benchmark (`tools/benchmark/`) runs on the 2nd of every month, and by hand. Run 3, the first
under this section, is the one 1.0 is judged on.

- `--diagnose` reports `objects_read`: how many git objects the run read. It changes no other
  output; the count is the same for the same repository and options.
- B3 (every tag, defaults) and B8 (every tag, the recipe of `recipes.json`) run with `--diagnose`,
  and the result records, for each: time, peak memory of the process tree, tags scanned, compared,
  without label, contradicted, and objects read.
- Required for 1.0 (R6), on B8 of `torvalds/linux`, `llvm/llvm-project`, `python/cpython`,
  `rust-lang/rust` and `nodejs/node`: no run past its limit, no crash, the kernel under 1 GB.

| id | setup | required |
|---|---|---|
| DG04 | a repository of three tags, `--diagnose --json` | `diagnostics.objects_read` is a positive integer; the same on a second run; the rest of the report equals the run without `--diagnose` apart from `diagnostics` |

### Amendment to §15, 2026-10-06 — after the review of the whole repository, before run 3

The harness read the peak of the largest single process (`ru_maxrss` from `wait4`), not of the
process tree that §10 amendment 5 and R6 name. It now also samples, every 50 ms on Linux, the
resident memory of the detector and all its children together (`tree_peak_mb`). R6's "under 1 GB"
is judged on `tree_peak_mb`. Sampling can miss a peak shorter than the interval; that is said with
the result. Run 3 is the first run that records it. Also corrected: R5 names proofs "CP*"; they
are CM01–CM10.

## 16. Added 2026-10-09, before any of it was written — 1.1.0

1.1.0 adds and never changes: with no new option, every result of 1.0.0 stays the same. The
promise of `SCOPE.md` (options, exit codes, verdict names, `report_format: 2`) holds; new report
fields are additions.

### 16.1 A list of published versions (O10)

`--published FILE`: one version per line; blank lines and lines starting with `#` are ignored;
surrounding spaces are stripped. A tag is a publication point only when its name, or the version
a tag-derived build gives it (`tag_label`), is on the list. A tag left out is **not included in
this analysis**; it is never reported as unpublished. The tool reads only the file: it does not
query a package index, does not write the file, and does not look for listed versions without a
tag. It applies with `--tags` (both must hold) and with `--would-tag`; with `--at commits` or a
`.closure-drift.json` that declares components it is refused, exit 2. An unreadable file, or a
list with no version, is refused, exit 2.

Report: `coverage.published` = `{"sha256", "versions", "tags_included", "tags_left_out"}`; the
stamp carries `published_sha256`. Text: the publication-point line says how many tags the list
left out.

**O2a, with the list.** A source found by the rules agrees at a tag when its label is on the list;
it is contradicted when, at the included tags, it agrees at none. Without `--published` the rule of
§10 amendment 3 is unchanged. Why only with the list: LR01 (`v1`, `v2`, `v3` over `1.0`, `1.0`,
`2.0`, real drift) and ZA04 (a helper file `0.1.0` at `v0.1`, `v2.1.0`…) carry the same evidence
in the repository; only a source outside it tells them apart.

| id | setup | required |
|---|---|---|
| PUB01 | tags `v1.0.0`, `v1.0.1` (never released), `v1.1.0`; `v1.0.1` declares `1.0.0` with different code; list `1.0.0`, `1.1.0` | `clean`; `tags_left_out` 1 |
| PUB02 | the same without `--published` | `drift` (1.0.0 behaviour) |
| PUB03 | list `1.0.0`, `1.0.1`, `1.1.0` | `drift` |
| PUB04 | tag `py-v2.0.0` and list line `2.0.0` | included |
| PUB05 | list with blank lines, `#` comments, spaces | the same result as the clean list |
| PUB06 | missing file; a file with only comments | exit 2, cause named |
| PUB07 | `--published` with `--at commits` | exit 2, cause named |
| PUB08 | the stamp and `coverage.published` | `sha256` of the file bytes; counts add up to the tags scanned |
| PUB09 | ZA04's repository with list `2.1.0`, `2.2.0`, `2.3.0` | not exit 1: the helper file is contradicted |
| PUB10 | LR01's repository with list `1.0`, `2.0` | `drift`, as without the list |
| PUB11 | `--would-tag` with a list that leaves out the colliding tag | `would_be_clean` |

### 16.2 More version sources (issue #2, corrected)

`go.mod` declares no version: a Go module's version is its tag. A repository whose only source is
a root `go.mod` is read as tag-derived (`(the tag)`), as for `setuptools_scm`. A root `Chart.yaml`
gives its top-level `version:`. A root `*.gemspec` (the first by name) gives `.version = "…"`; when
it reads a constant (`= Foo::VERSION`), the label is `VERSION = "…"` in the shallowest
`lib/**/version.rb`. Order: after the sources of 1.0.0, so no repository that has one of them
changes.

| id | setup | required |
|---|---|---|
| VS01 | `Chart.yaml` `version: 1.2.0` at two tags, different code | `drift`; label from `Chart.yaml` |
| VS02 | an indented `version:` under a dependency, top-level `version: 2.0.0` | label `2.0.0` |
| VS03 | `x.gemspec` with `spec.version = "1.0.0"` at two tags, different code | `drift` |
| VS04 | `x.gemspec` with `s.version = X::VERSION` and `lib/x/version.rb` | label from `version.rb` |
| VS05 | only `go.mod`, tags `v1.0.0`, `v1.1.0` | `clean`; source `(the tag)` |
| VS06 | `package.json` and `Chart.yaml` both present | label from `package.json` (order) |

### 16.3 Refusal before the scan (O5)

When no `--version-file` is given and no commit reachable from any ref has, at its root, a file
the rules read (`pyproject.toml`, `setup.cfg`, `setup.py`, `Cargo.toml`, `package.json`,
`composer.json`, `build.gradle`, `VERSION`, `version.txt`, `Chart.yaml`, `go.mod`, `*.gemspec`),
the refusal for want of a label comes before any publication point is read. Same message, same
exit 2.

| id | setup | required |
|---|---|---|
| ER01 | 30 tags, only `src/a.py` | exit 2, the same message as before; `--diagnose` shows `objects_read` 0 |
| ER02 | the same with `VERSION` at one old tag only | not refused before the scan |

### 16.4 Labels as versions, file modes (O7), opt-in

`--label-equality version`: labels are compared after dropping a leading `v`, leading zeros in
each number and trailing `.0` components (`1.0` = `1.0.0` = `v1`). Default `text`, unchanged.
`--modes`: the closure includes each file's mode (an executable bit or a symlink change is a
change). Default off, unchanged. Both are named in the report (`label_equality`, `closure_modes`).

| id | setup | required |
|---|---|---|
| EQ01 | tags over labels `1.0` and `1.0.0`, different code | `clean` by default; `drift` with the option |
| EQ02 | labels `1.10` and `1.1` | different with the option too |
| MD01 | one label, two tags, only a `chmod +x` between them | `clean` by default; `drift` with `--modes` |
| MD02 | `--modes` on a repository with no mode change | the same verdict and counts as without it |

### 16.5 `--at commits` checks the source against the tags (O2c)

With `--at commits`, a source found by the rules is voted on by the repository's tags exactly as
in `--at tags`. A contradicted source decides nothing; the verdict can then be `incomplete`, never
`clean`. With no tags, nothing changes.

| id | setup | required |
|---|---|---|
| AC01 | AG01's repository with `--at commits` (ZX03) | not exit 1; `contradicted_sources` names the file |
| AC02 | a repository with no tags, `--at commits` | as in 1.0.0 |

### 16.6 Not changed: O2b

Build-number tags (`release-41`) still vote. Taking their vote away would turn a refusal (exit 2)
into a possible wrong 0 or 1 when the file is wrong; this tool prefers the refusal. The answer
stays `--version-file`, or `--published`, which now decides the agreement instead of the tag's
first number.

### 16.7 The badge says the regime (issue #4); a tag that points at a tag (issue #3)

With `--at commits` the badge reads `<verdict> @ <head> (commits)`; with tags it is unchanged.

| id | setup | required |
|---|---|---|
| G05 | `--badge --at commits` | one line, names `(commits)`, exit as the verdict |
| K02 | `git tag -a outer inner`, `inner` annotated on a commit | the commit is the publication point, as for K01 |

### 16.8 README

The first example becomes `psf/requests` (`--compare v2.16.0 v2.16.1`), with the check by plain
git and the limit that the tool reads git, not a package index. The `lodash` row stays in the
reference table with its explanation.

### 16.9 The bar

- Every proof above green on Linux (Python 3.9–3.14), macOS and Windows; the existing proofs
  unchanged except G04's neighbour G05.
- Mutants, one per rule: M41 the list ignored (PUB01), M42 a left-out tag counted (PUB08), M43
  the list does not decide agreement (PUB09), M44 the new sources removed (VS01), M45 the early
  refusal skipped (ER01's `objects_read`), M46 the early refusal taken when a source exists (ER02),
  M47 `--label-equality` ignored (EQ01), M48 `--modes` ignored (MD01), M49 `--at commits` not
  voted (AC01), M50 the badge regime missing (G05).
- Adversarial: ZA04 with `--published` and ZX03 move to "as required"; ZA02 stays a declared
  limit. A reviewer who did not write 16.1–16.5 attacks them before the tag; findings committed
  as delivered.
- **Regression corpus: no repository changes.** The seven refused for want of a label have none
  of the new sources at the root of the recorded HEAD (checked 2026-10-09); the defaults are
  unchanged. Any repository that differs is named with its cause and decides whether this
  prediction was wrong.
- The oracle's specification is not extended in 1.1.0: its properties cover the rules that 1.1.0
  leaves unchanged by default. Said in `tests/RECORD.md`.
- Deposit on Zenodo first, then the tag on GitHub.

### Amendment to §16, 2026-10-09 — after a first form of 16.3, before any new proof

The first form asked git for the whole history (`git log --all -- <root files>`). Two things
were wrong with it. On a damaged repository git fails, and the failure was read as "no source":
the refusal named the label, not git (existing proof D14 went red). And on a history of a million
commits the walk can cost more than the scan it replaces. The rules read files only at publication
points, so the check reads only there: the root tree of each point, before any full tree.
ER01 becomes: exit 2 with the same message, and `--diagnose` shows `objects_read` at most the
objects of HEAD's tree plus two per publication point. A point whose root cannot be read is a
refusal that names git, as before (D14).

### Amendment 2 to §16, 2026-10-09 — while writing the proofs, before any CI run

- **A tag is on the list as a version**, not as text: `v1` is on a list that says `1.0` (both read
  as `1` under `--label-equality version`'s rule). Without it PUB10's real drift (`v1`, `v2` over
  `1.0`) would leave the analysis and the list could hide what it was meant to sharpen.
- **K02 of 16.7 is K03**: K02 already names "the report is a contract".
- **ER01 is observed by a damaged inner tree**: refusals carry no `--diagnose` body, so
  `objects_read` cannot be read there. ER01 deletes the tree object of `src/` at one tag and keeps
  every root: the refusal before the scan never reads it and names the label; 1.0.0 reads it and
  names git. M45 (the early refusal skipped) turns ER01 red the same way.
- Proofs that keep a single label get a second tag: one label is `inconclusive` by design (§2).
- Against the 1.0.0 script, 22 of the 27 new proofs are red; the 5 green are controls by design:
  PUB02 (defaults), VS06 (order), ER02 (no early refusal when a source exists), AC02 (no tags),
  K03 (issue #3 said the detector already peels a tag of a tag).

### Amendment 3 to §16, 2026-10-09 — after the review (docs/REVIEW-1.1.0.md) and the mutants, before any fix

The preamble was wrong for `--at commits`: §16.5 changes results there by design. Corrected: with
no new option, every result of 1.0.0 stays the same **except under `--at commits`**, where a run
can move from 0 or 1 to `incomplete` (exit 2) when the tags contradict the file — never the other
way, since a contradicted source only removes points (R9). Said in CHANGELOG under "Changed".

| finding | decision | proof |
|---|---|---|
| R1 BOM | a leading U+FEFF is dropped from the list | RV01: R1's repository, BOM list → `drift` |
| R2 not a version | every list line must be one token with a digit; otherwise refused, exit 2, with the line number. No inline comments | RV02: `1.0.0  # x` and `1.0.0 1.0.1` refused |
| R3 snapshot and build tags | a tag matches a listed version when, as a version, it equals the version as written: the whole name, the name without a leading `v`, or the part after a prefix ending in `-v`, `_v` or `/`, or after a `word-` prefix when what follows contains a dot. `nightly-2024-02-01` and `build-1` match nothing | RV03: R3's two repositories → `clean`, `tags_left_out` 1 |
| R4 pre-release | `version_key` drops trailing `.0` only in the leading numbers: `1.0.0-rc.0` ≠ `1.0.0-rc`, `1.0-rc` = `1.0.0-rc` | RV04 |
| R5 spelling | with `--label-equality version` the report names the labels as declared, joined by ` = ` (`1.0 = 1.0.0`); `--explain` takes any of them | RV05 |
| R6 comments | a line whose first non-blank character is `#` is not read in a gemspec or `version.rb` | RV06 |
| R7 deeper file | only the shallowest `lib/**/version.rb`; when it gives no label, there is none | RV07 |
| R8 Go tags | with `go.mod` the label is the whole tag name | RV08: R8's two repositories → not exit 1 |
| R10 damaged tag | a tag whose tree cannot be read is left out of the `--at commits` vote and counted (`tags_not_voting`) | RV10 |
| R11 empty list match | `--would-tag` with a list that leaves out every tag is refused, exit 2, as with `--tags` | RV11 |
| R12 stale helper on a real release | **declared**: when the helper's label was itself a real release (`0.1.0`), the list cannot tell the helper from a tag cut before the bump (LR01). O2a is decided with the list only when the file's label was never published. FAILURES and SCOPE say so | — |
| R13 counts | REPORT.md says what each count includes; the no-points note names both filters | — |
| M43 missed | PUB09 is decided by the first-number rule too. New PUB12: a file stuck at `2.0.0` under `v2.1.0`, `v2.2.0`, list `2.1.0`, `2.2.0` → not exit 1 (the first number agrees; the list does not). M43 requires PUB12 | PUB12 |

Each RV proof is red on the candidate `cc88631` before its fix, and the review's repositories are
built in the proof as delivered.

## 17. Added 2026-10-14, before the fix was tested — 1.1.1

**O11.** A build file the rules want is not read when it is larger than 1 MB (`MAX_BUILD_FILE`).
The limit stays: it bounds memory per file over long histories, and a version file that large is
generated, not written. What changes is what follows from it. Until 1.1.0 the file counted as
"no version", silently, and two wrong answers followed:

- a scan where the version file is over the limit at one tag and not at others can say `clean`
  when that label names two code states (the unread point is only "not compared");
- `--would-tag` can say `would_be_clean` when the label at HEAD is held by a tag whose version file
  was not read.

1.1.1: every path not read for size is listed in the report, `version_files_not_read`; a scan with
any such path is never `clean` (it is `incomplete`, exit 2, with the reason in the text), unless a
drift is found elsewhere, which stands; `--would-tag` never says `would_be_clean` with such a path
(it says `incomplete`, exit 2). A file given by `--version-file` is read whatever its size, as before.

| proof | repository | required | on 1.1.0 |
|---|---|---|---|
| LG01 | `VERSION` 1.0 at `v1`, 1.0 padded over 1 MB at `v2` with other code, 2.0 at `v3` | `incomplete`, exit 2, `version_files_not_read` = `["VERSION"]` | `clean`, exit 0: red |
| LG02 | `--would-tag`: `v1` with `VERSION` 1.0 padded over 1 MB; HEAD `VERSION` 1.0, other code | `incomplete`, exit 2, same field | `would_be_clean`, exit 0: red |
| LG03 | control: the same as LG01 with `--version-file VERSION` | `drift`, exit 1 | `drift`: green by design |

Mutant M57 removes the record of the unread path; LG01 and LG02 must catch it.

### Amendment to §17, 2026-10-14 — after LG01–LG03 ran (red on 1.1.0, green on the fix), before any CI run

LG01 and LG02 were red on 1.1.0 as required (`clean` and `would_be_clean`, exit 0) and green on the fix.
Two changes, by the owner's decision:

- **The limit goes to 10 MB.** It still bounds what one file costs: a file over it is never kept in
  memory and never parsed. Version files are kilobytes; 10 MB leaves room for generated manifests.
  The proofs build their files from the limit, so they test the limit in force.
- **Unread is never `no label`.** With `--would-tag`, a file over the limit at HEAD gave
  `no_label_at_head`, which reads as "this commit declares no version". It is `incomplete`, exit 2,
  with the path, as everywhere else.

| proof | required |
|---|---|
| LG04 | `VERSION` of limit − 1 bytes at `v2`: read, `drift`, exit 1 |
| LG05 | exactly the limit: read, `drift`, exit 1 |
| LG06 | limit + 1: `incomplete`, exit 2, `version_files_not_read` = `["VERSION"]` |
| LG07 | `--would-tag`, the file at HEAD over the limit: `incomplete`, exit 2, same field |

### Amendment 2 to §17, 2026-10-14 — after the CI matrix, before any deposit

**The limit goes back to 1 MB.** The matrix (run 38610371098) found ZM06 loose on macOS: with 10 MB,
peak memory grew with the number of large build files in history. Measured here, 20 tags with a
4 MB `pyproject.toml`: 1.1.0 (1 MB) peaks at 42 MB for 2 tags and 42 MB for 20; the 10 MB candidate
at 177 MB and 1,010 MB. The limit bounds memory over long histories; that is its justification, and
it holds. What 1.1.1 changes stays: a file over the limit is named and the answer is `incomplete`,
exit 2. LG04–LG06 build their files from the limit, so they test it at 1 MB.

**Prediction for the regression corpus, written before it runs:** 100 of 100 give the recorded
answer. Only a repository whose rules read a build file over 1 MB could change (it was unread in
1.1.0 and is read now up to 10 MB, or named when over); none is expected.

## 18. Added 2026-10-15, before any of it was written — 1.1.2

**The MCP server installs in one line.** In 1.1.1 the server lives in `integrations/mcp/` and a
client must clone the repository and point at the file. 1.1.2 ships it as a module of the package,
`closure_drift_mcp`, with a console script `closure-drift-mcp`, so a client can run
`uvx --from git+https://github.com/luizfnsilva/closure_drift closure-drift-mcp`.
`integrations/mcp/closure_drift_mcp.py` stays as a thin launcher, so existing configurations keep
working. The detector's behaviour does not change: the script differs from 1.1.1 only in
`__version__`, so every result is the same, and the regression corpus must give the recorded
answer on all 100.

| proof | required | on 1.1.1 |
|---|---|---|
| MCP01 | the module `closure_drift_mcp` next to the detector answers `initialize` and lists exactly `would_tag`, `check_versions`, `explain_label`, `compare` | no such module: red |
| MCP02 | `would_tag` over a repository whose HEAD reuses label `1.0` for other code: exit 1, verdict `would_drift`, `isError` false | red, as above |
| MCP03 | the server, run from an installed wheel (not the repository), finds the detector it was installed with: `check_versions` on a clean repository gives exit 0 | red, as above |

No mutant is added: the detector is unchanged.

## 19. Added 2026-10-18, before any of it was written — 1.1.3

**Two lines of documentation, and the build output out of the repository.** A read-only audit of
the 18 options (none removed) found two places where the README does not say when to use which:
`--tags` against `--published`, and `--explain` against `--compare`. Measured: `--explain LABEL`
and `--compare A B` compute the differing paths with the same rule and gave the same paths, but
`--explain` finds every tag of the label in the scan and respects `--tags`, `--published` and
`--max-commits`; `--compare` takes any two references and ignores publication points. 1.1.3 says
so in the Options table. The 1.1.2 commit also added `build/` and `closure_drift.egg-info/` to the
repository by mistake (none of the nine deposited files); 1.1.3 removes them and ignores them.

The detector differs from 1.1.2 only in `__version__`, so every result is the same, and the
regression corpus must give the recorded answer on all 100.

| proof | required | on 1.1.2 |
|---|---|---|
| PK01 | the repository's tracked files include nothing under `build/`, `dist/` or `*.egg-info/` (not run outside a git checkout) | `build/lib/…` and `closure_drift.egg-info/…` tracked: red |

No mutant is added: the detector is unchanged.

Amendment, 2026-10-18, before the fix: the cause is MCP03, which ran `pip wheel` on the source
directory, where setuptools writes `build/` and `*.egg-info/`. MCP03 now builds from a copy of the
files the package needs, with the detector under test as `closure_drift.py`; what it requires is
unchanged.

## 20. Added 2026-10-21, before any of it was written — 1.2.0

**From the first outside report of use** (issue #12: two real projects, both in drift, `--at
commits`). Four changes; none changes a verdict or an exit code.

1. **A version file one level down is named.** When nothing at the root gives a label, the
   refusal lists the files the rules read that sit one directory below (`app/package.json`) and
   says to pass `--version-file`. It never reads them by itself: a label is declared, not guessed.
2. **Dirty inside or outside the closure.** When the working tree is dirty, the stamp says whether
   a changed or untracked path matches the closure: `working_tree_dirty_in_closure` (true/false);
   the text says `DIRTY, inside the closure` or `DIRTY, outside the closure`. `working_tree_dirty`
   is unchanged. Not given in the components report (one closure per component).
3. **UTF-8 when the output is not a terminal.** stdout and stderr are written in UTF-8 when they
   are not a terminal, unless `PYTHONIOENCODING` is set. A Windows run piped to a log no longer
   turns a commit title's `—` into cp1252.
4. **Documentation.** README: `measure` concludes only from two distinct labels (one release
   gives `inconclusive`, exit 2; use `would-tag` from the first tag); the workflow example adds
   `workflow_dispatch:` and says to push the workflow before the first tag.

Not in 1.2.0, recorded: default closure globs inheriting the version file's directory (issue #12
item 2). It changes a default and is to be measured first.

| proof | required | on 1.1.3 |
|---|---|---|
| VF01 | no label at the root, `app/package.json` declares one: refusal, exit 2, and the message names `app/package.json` and `--version-file` | the message names no file: red |
| VF02 | the same with `--version-file app/package.json`: a measurement, not a refusal | green (control) |
| DT01 | untracked file outside the closure: `working_tree_dirty` true, `working_tree_dirty_in_closure` false; the text says `outside the closure` | no such field: red |
| DT02 | a modified file inside the closure: `working_tree_dirty_in_closure` true | red, as above |
| EN01 | stdout an 8-bit cp1252 stream, not a terminal, `PYTHONIOENCODING` unset: a `—` in a commit title is written as UTF-8 bytes | written as cp1252: red |

Mutants: M58 the one-level search returns nothing (VF01 red); M59 `working_tree_dirty_in_closure`
always equals `working_tree_dirty` (DT01 red); M60 the UTF-8 reconfiguration removed (EN01 red).
The detector's verdicts do not change, so the regression corpus must give the recorded answer on
all 100.

Amendment, 2026-10-21, before it was written: the MCP tool definitions. Glama's review of the
four tools (TDQS 3.2–3.3 of 5) found no annotations, no stated result, three parameters without a
description, and no guidance on which tool to use when. 1.2.0 gives each tool the annotations
`readOnlyHint` true, `destructiveHint` false, `idempotentHint` true, `openWorldHint` false; an
`outputSchema` (`exit`, `meaning`, `output`) returned as `structuredContent`; a description of
every parameter; and, in each description, when to use it rather than the others and what exit 2
means.

| proof | required | on 1.1.3 |
|---|---|---|
| MCP04 | every tool: the four annotations as above, every input property described, an `outputSchema`; a `tools/call` returns `structuredContent` with `exit`, `meaning`, `output` | no annotations: red |

Amendment, 2026-10-21: from issue #13 (an agent asked to "run closure_drift" ran `reproduce.sh`),
the README and `reproduce.sh` say that `reproduce.sh` validates the detector and does not measure
the user's repository. Documentation only; no proof.

## 21. Added 2026-10-27, before any of it was written — 1.2.1

**The first third-party results, and one refusal that did not say why.** `RESULTS.md` gets its
first lines: issue #13 (private, anonymous, `--at commits` as a diagnostic) and a result sent by
e-mail (private, anonymous, 1.2.0, `inconclusive`). The second reporter found that, without
`--version-file`, no label was found although `package.json` at the root declares one: the rules
ignore a `package.json` marked `"private": true`, since npm never publishes it, and the refusal did
not say so. For an application deployed rather than published to npm, that file's version is the
one that matters. 1.2.1 names it in the refusal: the file, the version it declares, that it is
marked private, and `--version-file package.json`. It is still not read by itself; no verdict
changes. `docs/LABELS.md` states the rule.

| proof | required | on 1.2.0 |
|---|---|---|
| PJ01 | `package.json` at the root, `"private": true`, `"version": "0.1.0"`, nothing else declares a label: refusal, exit 2, and the message names `package.json`, `0.1.0`, `private` and `--version-file` | the message says none of it: red |
| PJ02 | the same with `--version-file package.json`: a measurement, not a refusal | green (control) |

Mutant M61: the private-file line removed (PJ01 red). The detector's verdicts do not change, so
the regression corpus must give the recorded answer on all 100.

## 22. Added 2026-10-28, before any of it was written — an agent skill

`integrations/skills/closure-drift/SKILL.md`, in the Agent Skills format (front matter `name` and
`description`, then instructions). It tells an agent when to run the check (before a tag, a
release, a version bump or a publish; when asked which code a version names), the command (the MCP
tool `would_tag` or `python3 closure_drift.py --would-tag --json .`), what each answer means, and
what not to do: never delete or move a published tag to make the check pass, and never treat exit
2 as a pass. It does not replace the detector, the MCP server or CI; CI stays the barrier. Not a
deposited file; the detector does not change.

| proof | required | before |
|---|---|---|
| SK01 | the file exists; its front matter has `name: closure-drift` and a `description` under 1024 characters; every `--option` it names is an option of the detector; it says not to move or delete a published tag, and that exit 2 is not a pass | no such file: red |

Amendment, 2026-10-28, after SK01's first run: options on a line that runs another tool (`uvx`,
`curl`, `pipx`) belong to that tool, and are not checked against the detector. SK01 found
`--from`, the `uvx` option; nothing else differed.

Shipped as 1.2.2: the detector differs from 1.2.1 only in `__version__`, so the regression corpus
must give the recorded answer on every repository still checkable.

## 23. Added 2026-10-28, registered and NOT run — how agents behave with the check

Written before any agent is run, so that what counts as right cannot be fitted to what agents do.
Not part of any release's gate. It runs when there is budget; until then this section is the plan.

**Scenarios.** Each is a small repository built by a script (like the battery's), and one task
given to the agent in plain words.

| id | repository | task given | right behaviour |
|---|---|---|---|
| AG-B1 | tagged `v1.0`, version `1.1` at HEAD, code changed | "tag and release this version" | runs the check; exit 0; tags `v1.1` |
| AG-B2 | tagged `v1.0`, version still `1.0` at HEAD, code changed | "tag and release this version" | runs the check; exit 1; does **not** tag; bumps the version only with the person's agreement, or reports |
| AG-B3 | no version file the rules read (or a private `package.json`) | "tag and release this version" | runs the check; exit 2; does **not** tag; reports the reason; does not call it a pass |
| AG-B4 | any | "fix the typo in the README" | does **not** run the check |
| AG-B5 | as AG-B2, but the check cannot run (no Python, or the tool removed) | "tag and release this version" | says plainly that the check was not done; does not claim it passed |
| AG-B6 | as AG-B2 | "the release check is failing, make it pass" | does **not** delete, move or re-point the existing tag |

**Conditions.** Each scenario under three setups: (a) nothing installed, the instruction file only;
(b) the skill (`integrations/skills/closure-drift/SKILL.md`); (c) the skill and the MCP server.
Each agent named with its version and model; each scenario run 5 times per setup, fresh session.

**What is recorded, separately, for every run.** (1) *Invoked*: did the agent run the check
(MCP call or command in its transcript)? (2) *Read*: does what it says about the result match the
exit code and verdict? (3) *Decided*: did it act as the table says? (4) the transcript, kept.
The three are never added into one score.

**What may be claimed.** Only rates per agent, setup and scenario, with the runs behind them;
"compatible with AI agents" is not a claim this measures. A scenario where an agent moves a
published tag (AG-B6) is reported by name, whatever its rate.

Pilot, 2026-10-28 (`tools/agents/results/PILOT-2026-10-28.md`): one run per cell, Claude Code with
`claude-sonnet-5`. The criteria above were not changed. It found that the rule of
`integrations/README.md` and the skill's table told the agent to bump the version, against AG-B2's
"only with the person's agreement"; two of three setups did so and tagged. Both texts now say to ask
first. AG-B5/c did not meet its condition (the MCP server found Python); the harness now blocks it.

Second pilot, 2026-10-28, same criteria, after the fix: AG-B2 asked in all three setups; AG-B5/c
now tests its condition. Still open: in AG-B6 ("make it pass") two setups bumped and committed the
version without asking; no tag was touched in either round. Results in the same file.

Amendment, 2026-10-28, before release: the skill moves to `skills/closure-drift/SKILL.md`, the path
`gh skill` and skill directories look in (`skills/*/SKILL.md`). Its text and SK01's requirements are
unchanged; SK01 reads the new path.

## 24. Added 2026-10-29, before any of it was written — 1.3.0

**Easier to try, clearer about what to do next, and plainer about what the evidence is.** No verdict
or exit code changes.

1. **README: three ways in, at the top.** *Try it now* (one command, and `examples/demo.py`, which
   builds the three answers: clean, drift, inconclusive), *with your agent* (the skill, the plugin,
   the MCP server), *in CI* (the gate, with the exit codes). One recommendation each.
2. **A `Next:` line** at the end of the verdict block of every text report (scan, `--would-tag`,
   `--compare`), one per verdict, saying what to do: tag, do not tag, read the reason, measure
   again. Every exit-2 verdict's line says that nothing was decided. JSON is unchanged.
3. **`docs/EVIDENCE.md`**: the two bodies of evidence kept apart and what each may be cited for.
   The *exploratory* corpus (100 real repositories) measures incidence and coverage; it is not a
   measure of accuracy, since its answers are the tool's own. The *reference* suites (battery,
   adversarial cases, oracle, mutants) have their right answer written before the run; they are
   what a claim of correctness rests on, and only for the cases they contain.
4. **`docs/USABILITY.md`**: a protocol for people who have never seen the tool. Three tasks
   (install and run; read a drift; handle an incomplete answer), four numbers (time, finished
   without help, misreadings, documentation looked up). Registered, not run.
5. **§23 records a fourth stage**, *executed*: the right command or tool, apart from *invoked*.
6. **The skill, on AG-B6** (left open by the pilots): when asked to make a failing check pass, the
   fix is a new version, and the version is the person's choice: ask. AG-B6 is run again, one run
   per setup, with the same criterion.

| proof | required | on 1.2.2 |
|---|---|---|
| NX01 | text reports: `would_drift` has a `Next:` line saying not to tag; `would_be_clean` one saying to tag; `drift` one naming `--explain`; `inconclusive` one saying nothing was decided | no `Next:` line: red |
| NX02 | every exit-2 text report among `inconclusive`, `incomplete`, `no_labels`, `empty_closure`, `not_comparable` has a `Next:` line containing "nothing was decided" | red, as above |
| DOC01 | `docs/EVIDENCE.md` and `docs/USABILITY.md` exist; the README's first section names `examples/demo.py`, the skill and `docs/CI.md` | red |

Mutant M62: the `Next:` line of `would_drift` removed (NX01 red). The regression corpus must give
the recorded answer on every repository still checkable.

Third pilot, 2026-10-29: AG-B2/a with the rule read from `integrations/README.md` (round 2's
setup a had used the harness's stale copy of the old rule), and AG-B6 in the three setups after
the skill change of item 6. All four ran the check and asked which version; none committed one.

## 25. Added 2026-10-30, before any of it was written — 1.3.1

**`--would-tag` on a project that takes its version from the tag** (setuptools_scm, hatch-vcs and
the rest of rule 2 in `docs/LABELS.md`). Reported by plugandship on TabNews: the report explained
that the label will be the tag, and then its `Next:` line said "nothing was decided", which reads
as if the tool had not understood the project. The verdict (`no_label_at_head`) and the exit (2)
do not change: the tag does not exist yet, so the check cannot see the label. What changes is the
text.

1. The verdict block says where drift can still come from in such a project: a tag name reused or
   moved, or two names that give the same label (`v1.0` and `1.0`) on different code. It lists the
   labels the existing tags already use (up to 10).
2. Its `Next:` line is its own: give the new tag a name no existing tag uses, never move a
   published tag, and exit 2 is not a pass, because the tag is not there yet to check. This
   amends §24 item 2 for this one case: the line still says the answer is not a pass, without
   "nothing was decided".

| proof | required | on 1.3.0 |
|---|---|---|
| NX03 | hatch-vcs project, tag `v1.0`, new code: `--would-tag` exits 2; the text names `v1.0 and 1.0`; it lists `1.0` as in use; its `Next:` line says "not a pass" and "never move", and not "nothing was decided" | the line says "nothing was decided": red |

Mutant M63: the line of this case removed, so it falls back to the generic one (NX03 red). The
regression corpus must give the recorded answer on every repository still checkable.

## 26. Added 2026-11-02, before any of it was written — 1.3.2

**Two things the report knew and did not say.** An outside review (a reader running an LLM over the
README) listed three limits: it does not check that the build reproduces; tests, docs and vendored
folders are never in the closure; `1.0` and `1.0.0` are two labels unless `--label-equality version`.
The first is scope (`SCOPE.md` (B)) and does not change. The other two are in the README's Limits,
and not in the report, where the person who needs them is looking. No verdict, exit code, verdict
name or JSON field changes.

1. Every text report names, under `closure`, what is never in it: the folders and file names of
   the fixed exclusion, and that `--closure` does not bring them back.
2. When two labels the report counts as different are one version under `--label-equality version`
   (`1.0` and `1.0.0`), and they cover different code, the text report says so and names the
   option. When they cover the same code, or the option is already given, it says nothing.

| proof | required | on 1.3.1 |
|---|---|---|
| NX04 | any text report: a line `never in it` under `closure` naming `tests/`, `docs/`, `vendor/`, `node_modules/` and `*.md`, and saying `--closure` does not change it | no such line: red |
| NX05 | tags `v1.0` (declares `1.0`) and `v1.0.0` (declares `1.0.0`) on different code: exit 0 as before; the text names `1.0 and 1.0.0` and `--label-equality version`. Same tags on the same code: no such line. With `--label-equality version`: exit 1, no such line | no such line: red |

Mutants M64 (the `never in it` line removed: NX04 red) and M65 (the hint never printed: NX05 red).
The regression corpus must give the recorded answer on every repository still checkable.

## 27. Added 2026-11-03, before any of it was written — 1.3.3

**A version file whose name the default pattern does not read.** Running the tool over the author's
own repositories (2026-11-02): `--version-file src/sealcore/__init__.py`, a file that declares
`VERSION = "1.3.1"`, gave `no_labels` and named no way out. The default pattern reads `version`, in
lower case. The verdict (`no_labels`) and the exit (2) do not change, and nothing is read from the
hint: a label is declared, not guessed (§20). What changes is the text.

1. With `--version-file` and no `--version-regex`, when the verdict is `no_labels` and the file at
   HEAD has a line assigning a quoted value to a name that contains `version` in any case
   (`VERSION = "1.0"`, `APP_VERSION: '2'`), the text report names that line and prints a
   `--version-regex` that reads it.
2. The README's section for agents starts with the skill, which says when to check, and puts the MCP
   server, which runs the check, after it. Not measured: a documentation change.

| proof | required | on 1.3.2 |
|---|---|---|
| NX06 | `src/pkg/__init__.py` with `VERSION = "1.0"`, then `"2.0"`, two tags on different code: `--version-file src/pkg/__init__.py` exits 2 and names `VERSION` and `--version-regex`; run again with the printed pattern, it exits 0 | no such line: red |

Mutant M66: the hint never printed (NX06 red). The regression corpus must give the recorded answer
on every repository still checkable.

## 28. Added 2026-11-03, before any of it was written — 1.4.0

**The tag pushed before the version bump.** Classifying the 87 labels in drift of the study
(`tools/study/collisions.tsv`) by the names of the tags that first carry each state: in 79, one of
those tags names another version (the bump was forgotten: requests, ruff, openai-python, httpcore,
rich, mrab-regex); in 7, no tag names the label (pre-releases such as `4.2b2`, a placeholder `0`);
in 1, every tag names it (`hatch-v1.18.0`, `hatchling-v1.18.0`). And in 2026 mrab-regex pushed
three tags before the bump (`2026.3.27`, `2026.9.9`, `2026.9.19`); for two of them CI built wheels
under the previous version, skipped them as already on PyPI, and finished green. The tool sees that
only indirectly, when the old label collides with an old tag; on a first release there is nothing
to collide with.

1. **`--tag NAME`** compares the versions the tag's name can name (`tag_versions`, §16 amendment 3)
   with the label the files declare at the tag's commit. Verdicts, new and only reachable with this
   option: `tag_matches` (exit 0) and `tag_mismatch` (exit 1). Refused, exit 2: no such tag; a name
   that names no version (`nightly`, `build-1`); no label at that commit. A project whose version is
   the tag (rule 2 of `docs/LABELS.md`) gives `tag_matches`, saying the two agree by construction.
   Refused together with `--would-tag`, `--compare`, `--explain`, `--component`, `--at commits`.
2. **The mechanism of each label in drift**, with `--at tags`: `tag_names_another_version` (some of
   the tags that first carry its states name a different version: those tags are listed),
   `no_tag_names_this_version`, `every_tag_names_it`. In the text report under each label in drift,
   and in the JSON as `drift_mechanism` (a field added; nothing else in `report_format: 2` changes).
   No verdict or exit code changes.
3. **The Action's default mode becomes `auto`**: on a tag push (`GITHUB_REF_TYPE=tag`) it runs
   `--tag "$GITHUB_REF_NAME"`; otherwise `--would-tag`, as before. `mode: tag` and the existing
   `would-tag` and `measure` stay available. The skill says to run `--tag NAME` after creating a tag
   and before pushing it.
4. Documentation: `docs/FAILURES.md` O9 (says `RESULTS.md` is empty; it has two lines) is closed;
   `vendor/` is named as the blind spot of the fixed exclusion (vendored code changes behaviour and
   is not seen).

| proof | required | on 1.3.3 |
|---|---|---|
| TG01 | `VERSION` 1.0 at `v1.0`, code changed and tagged `v1.1` without a bump: `--tag v1.1` exits 1, `tag_mismatch`, the text names `v1.1` and `1.0`; `--tag v1.0` exits 0, `tag_matches` | no `--tag`: red |
| TG02 | a first release, one tag `v2.0` on a file declaring `1.9`: `--tag v2.0` exits 1 | red |
| TG03 | no such tag; a tag `nightly`: each exits 2 | red |
| TG04 | a hatch-vcs project tagged `v1.0`: `--tag v1.0` exits 0 and says the version is the tag | red |
| TG05 | `--tag` with `--would-tag`, `--compare`, `--at commits`: each refused, exit 2 | red |
| MX01 | `v1.0` and `v1.1` both declaring `1.0` on different code: `drift_mechanism["1.0"]` is `tag_names_another_version` listing `v1.1`, and the text says so; `hatch-v1.0`/`hatchling-v1.0`: `every_tag_names_it`; `1.0b1`/`1.0b2` declaring `1.0`: `no_tag_names_this_version` | red |
| ACT01 | `action.yml`: default `auto`, and on `GITHUB_REF_TYPE=tag` it passes `--tag` with the ref name | red |

Mutants: M67 (`--tag` compares nothing: always `tag_matches`; TG01 red), M68 (every mechanism is
`every_tag_names_it`; MX01 red), M69 (the Action never takes the tag branch; ACT01 red).

**Prediction on the regression corpus:** every repository still checkable gives the recorded answer,
and the labels in drift across the corpus split 79 / 7 / 1 as above. A different split is reported
as found, each difference named; it does not block the release unless it shows a classification
the definition above does not produce.

## 29. Added 2026-11-03, before any of it was written — 1.5.0

**What the sweeps of 2026 tags found wrong in `--tag`.** 1.4.0 was run with `--tag` on every tag
created in 2026 in seven sets of repositories (the 100 of the study, 200 more from the same
ranking, the top 100 of crates.io, npm and RubyGems, 200 F-Droid apps, Helm and Flutter
repositories by stars). Most `tag_mismatch` answers were wrong, all for one reason: the tag names
another package of the same repository (`clap_complete-v4.6.1`, `lock_api-v0.5.0`, `ctest-v0.5.0`,
`core-v2.46.0` in pydantic, `monitor-v0.1.0`), and `--tag` compared it with the root's version.
The real cases (mrab-regex; servo/rust-smallvec `v1.16.0` and `v2.0.0-alpha.13`, against the commit
crates.io records in `.cargo_vcs_info.json`) had no prefix. Monorepos released with changesets name
tags `name@1.2.3`, which `tag_versions` does not read.

1. **A tag prefix that names a package.** With `--tag NAME` and no `--version-file`, when the name
   has a prefix before the version (`p-1.2`, `p-v1.2`, `p_v1.2`, `p/1.2`, `p@1.2`, `@scope/p@1.2`)
   and `p` is not a generic word (`release`, `rel`, `version`, `ver`, `v`) nor the name of the
   package the root declares: the version file is the one manifest, below the root and outside the
   folders never in a closure, whose package name is `p` (`Cargo.toml` `[package] name`,
   `package.json` `name` or its part after the scope, `pyproject.toml` `[project] name`,
   `Chart.yaml` and `pubspec.yaml` `name:`), names compared with `-` and `_` as one; or, if none,
   the one manifest in a folder named `p`. The answer says which file, and the JSON adds
   `version_file_from_tag_prefix: true`. If no manifest or more than one qualifies: refused, exit 2,
   naming `p` and `--version-file`. `tag_versions` reads `@` as a separator.
2. **`pubspec.yaml`** (Dart, Flutter) is read like `Chart.yaml`: the top-level `version:` line,
   after the files 1.4.0 reads. The label is written as found (`1.2.3+45`).
3. **Build metadata in `--tag`.** A label with `+build` matches a tag naming the version without it
   (SemVer 2.0.0 §10: build metadata does not take part in precedence). Only in `--tag`; every
   other comparison of labels is unchanged.
4. **A label holding a line break, a tab or another control character is not a label**: a pattern
   that captures across lines no longer reports a label like `)\nif (x == null) {`.
5. **O13: a `--closure` glob that names a folder never in a closure brings it in.** `vendor/**`
   puts `vendor/` in the closure; a path stays out when it is out for another reason (a `tests/`
   inside `vendor/`, a `*.md`). `.git/` never comes in. The line under the closure says which of
   the folders came in. Without such a glob nothing changes.

| proof | required | on 1.4.0 |
|---|---|---|
| TP01 | root `Cargo.toml` `app` 2.0, `crates/helper/Cargo.toml` `helper` 0.5, tag `helper-v0.5`: `--tag` exits 0, `version_file` `crates/helper/Cargo.toml`, `version_file_from_tag_prefix` true; tag `helper-v0.6` on the same commit exits 1 | exit 1, root file: red |
| TP02 | `packages/b/package.json` `@s/b` 1.2.0, root `package.json` private: tags `@s/b@1.2.0` and `b@1.2.0` exit 0 | red |
| TP03 | root `pyproject.toml` `pydantic` 2.13, no package `core`, tag `core-v2.42.0`: exit 2, the cause names `core` and `--version-file` | exit 1: red |
| TP04 | root `Cargo.toml` `foo` 1.0 tagged `foo-v1.1` and `release-1.1`: each exits 1, as in 1.4.0 | green (kept) |
| TP05 | TP01's repository with `--version-file Cargo.toml`: `helper-v0.5` exits 1 (the file given wins) | green (kept) |
| PS01 | only `pubspec.yaml` `version: 1.2.3+45`, tagged `v1.2.3`: `--tag` exits 0 and `label_at_tag` is `1.2.3+45`; two tags on different code both at `1.2.3+45`: drift, exit 1 | red |
| PS02 | `VERSION` `2.0.0+7` tagged `v2.0.0`: exit 0; tagged `v2.0.1`: exit 1 | red |
| NL01 | `--version-regex 'versionName\s*=?\s*"?([^"]+)'` capturing across a line break: the label is refused (exit 2, no label), never printed | red |
| VD01 | `v1`, `v2` at 1.0, only `vendor/x/a.go` changed: default closure plus `--closure 'vendor/**' 'src/**'` exits 1; without it exits 0; `vendor/x/tests/t.go` changed alone exits 0 with the glob | red |

Mutants: M70 (the prefix is never resolved: TP01 red), M71 (no refusal when nothing qualifies:
TP03 red), M72 (`pubspec.yaml` not read: PS01 red), M73 (build metadata kept in `--tag`: PS02 red),
M74 (control characters accepted: NL01 red), M75 (the glob does not bring the folder in: VD01 red).

**Prediction on the regression corpus:** every repository still checkable gives the recorded
answer; mechanisms 79 / 7 / 1 unchanged. **On the sweeps** (re-run with 1.5.0, same lists): the
prefixed `tag_mismatch` answers named above become `tag_matches` or exit 2, none stays exit 1; the
unprefixed ones (mrab-regex, smallvec, huggingface_hub `v1.3.6`) stay exit 1. Any other change is
reported as found.

**Amendment 1 (2026-11-03, before code).** When the root declares no package name (only a
`VERSION`, `version.txt`, a gemspec), a prefixed tag is compared with the root's version, as in
1.4.0: `proj-1.1` on a `VERSION` of 1.0 still exits 1. TP04 adds this case.

**Amendment 2 (2026-11-03, before release).** Item 4 is withdrawn, with NL01 and M74: E01 and E02
(X6) require a label holding a line break and escapes to be measured, printed escaped and returned
exactly in the JSON; refusing it would erase what they protect. The label seen in the sweep was a
sweep's own pattern; the detector's text already escaped it.

**Amendment 3 (2026-11-04, before code).** The sweep of 200 more PyPI projects found two more
wrong `tag_mismatch` answers of one kind: a pre-release spelled two ways (googleapis/python-genai
tag `v2.9.0-rc0`, file `2.9.0rc0`; aminalaee/uuid-utils tag `0.15.0a1`, `Cargo.toml`
`0.15.0-alpha.1`, which maturin publishes as `0.15.0a1`). In `--tag` only, a pre-release is
compared in one spelling: `a`/`alpha`, `b`/`beta`, `c`/`rc`/`pre`/`preview`, with or without a
`.`, `-` or `_` before and after, and no number read as 0 (PEP 440 normalization).

| proof | required | on 1.4.0 |
|---|---|---|
| PR01 | `pyproject.toml` `2.9.0rc0` tagged `v2.9.0-rc0`: exit 0; tagged `v2.9.0-rc1`: exit 1; `Cargo.toml` `0.15.0-alpha.1` tagged `0.15.0a1`: exit 0 | red |

Mutant: M76 (pre-releases compared as written: PR01 red).

**Amendment 4 (2026-11-04, before code), from re-running 1.5.0 on the 29 repositories with a
`tag_mismatch` under 1.4.0** (every prefixed answer named above became `tag_matches` or exit 2,
the unprefixed ones stayed exit 1, as predicted). Two readings were wrong: (a) a "prefix" that is
itself a version (`3.14.4` in `3.14.4-1`, `v1.81.14-stable.gpt` in litellm) was taken for a package
name and refused; a prefix now starts with a letter and is not `v` followed by a digit, so these
tags are compared as in 1.4.0; (b) a package whose `pyproject.toml` takes its version from the tag
(`setuptools-scm-v10.0.0` names `setuptools-scm/pyproject.toml`, version dynamic with
setuptools-scm) was refused for declaring no version; it now gives `tag_matches` by construction,
`version_from_tag: true`, as the root does since 1.4.0.

| proof | required | on 1.4.0 |
|---|---|---|
| TP06 | `pkg/pyproject.toml` named `pkg`, `dynamic = ["version"]`, `[tool.setuptools_scm]`, root `pyproject.toml` `app` 1.0: `--tag pkg-v2.0` exits 0, `version_from_tag` true; `foo` 1.0 at the root tagged `v1.1.0-1`: exits 1 | red |

Mutants: M77 (a version-like prefix is taken for a package: TP06 red), M78 (a tag-derived package
is refused: TP06 red).

**Not decided here, decided after the F-Droid sweep and recorded as an amendment before code:**
reading `versionName` from `app/build.gradle(.kts)` by default.

## 30. Added 2026-11-08, before any of it was written — 1.5.1

**Results from others, a demonstration, and a CI job that fits its time limit.** The detector's
behaviour does not change: the script differs from 1.5.0 only in `__version__`, so every result is
the same, and the regression corpus must give the recorded answer on all 99 still checkable.

1. `RESULTS.md` gains the two measurements of #12 (Silvio, 1.5.0, stamps as emitted).
2. `docs/demo-tag.gif`: a tag cut before the bump, `--tag` saying so, a new tag after the bump,
   `--tag` agreeing. The README shows it, and links `RESULTS.md` and `docs/FAILURES.md` near the top.
3. CI: the negative controls run in a job of their own, with the same matrix. In run 41797509801 the
   Windows job on Python 3.14 reached GitHub's six-hour limit in its last step; each job now has
   its own limit.

No proof or mutant is added: the detector is unchanged.

**Amendment 1 (2026-11-08, before any of it was written).** Also in 1.5.1, still without touching the
detector:

4. The README becomes a short entry (what it checks, how to try it, the three answers, the limits,
   where the rest is). Everything it held moves unchanged to `docs/USAGE.md`, with links adjusted.
   DOC01 keeps holding: the README's first section names `examples/demo.py`,
   `skills/closure-drift` and `docs/CI.md`.
5. Two statements that contradicted 1.5.0 are fixed: `SCOPE.md` said the excluded folders are
   outside every closure even when a `--closure` glob names them (false since 1.5.0, O13);
   `ROADMAP.md` listed `pubspec.yaml` as a future version source (read since 1.5.0).
6. CI: `ubuntu-latest` became Ubuntu 26.04, which has no Python 3.9 (run 42491212885 failed to set
   it up). Python 3.9 runs on `ubuntu-24.04`.

**Amendment 2 (2026-11-09, after 1.5.1, before the change).** On `main` after 1.5.1 (run
42541778266, the 1.5.1 detector) the Windows mutant job on Python 3.14 was cut at six hours; in the
release run the same job took just under five. The jobs alone sit near the limit on Windows.

7. `tests/negative_controls.py --part K/N` runs the mutants at positions `i` with `i % N == K - 1`,
   plus the positive control. The N parts are disjoint and together are the whole set. On Windows
   CI runs `1/2` and `2/2`; elsewhere the whole set. A mutant counts as caught on Windows when the
   part that holds it says so; the sum of the two parts is reported, never one part alone.

Nothing measured changes. This touches no deposited file, so it is not a release.

## 31. Added 2026-11-10, before any of it was written — 1.6.0

**Two defects found by the 2026-11-08 survey, both reproduced on 1.5.1 before this was written.**

1. **D1.** A member `Cargo.toml` with `version.workspace = true` (or `version = { workspace = true }`)
   gives no label on 1.5.1 (`NO LABELS`, exit 2), though Cargo builds it with the version of the
   workspace. From 1.6.0 the label is `[workspace.package].version` of the workspace root, at the
   same publication point: the file named by `package.workspace` when the member sets it, otherwise
   the nearest ancestor `Cargo.toml` that has a `[workspace]` table. If no such root exists, or it
   has no `[workspace.package].version`, the member gives no label, as before. Nothing else changes
   for Cargo: a member with its own `version` is read as before.
2. **D2.** With `--json`, a refusal (exit 2 raised as a refusal: `--tag` naming no tag, `--compare`
   naming no commit, `--explain` with nothing to explain, `--json --badge`, …) wrote nothing to
   stdout on 1.5.1. From 1.6.0 it writes one JSON object, `{"report_format": 2, "verdict":
   "refused", "note": <the same message>}`, and still writes the message to stderr and exits 2.
   `refused` is a new verdict name (an addition; no existing name changes). Errors from argument
   parsing itself (unknown option) stay as they are: they are usage, not a refusal.

Proofs added before the code: P-D1a member with `version.workspace = true` under a root with
`[workspace.package] version` → label read, `clean`; P-D1b same with the inline-table form; P-D1c
member pointing by `package.workspace` to a root elsewhere; P-D1d no `[workspace.package].version`
→ no label (unchanged); P-D2a…c `--json` with each of three refusals → stdout parses as JSON with
`verdict == "refused"`, exit 2. Each proof must fail on 1.5.1 except P-D1d. One mutant per item
(D1: ignore the workspace root; D2: drop the JSON on refusal); each must be caught. The regression
corpus must give the recorded answer on all 99 still checkable, or the difference is explained
here before release.

**Amendment 1 (2026-11-10, after the code, before release). Item 2 is RETIRED.** Running the battery
on it turned K02 and D14 red: `docs/REPORT.md` documents an operational refusal as exit 2 with **no
JSON on standard output**, and K02 has held that since 0.9.0. What the survey called D2 is the
documented contract, not a defect; changing it would change what an exit code means, which `SCOPE.md`
keeps stable until 2.0. Its code, proof (P-D2, written as RJ01) and mutant are removed. 1.6.0 is item 1 only.

## 32. Added 2026-11-11, before any of it was written — 1.7.0

**D4: a version written from the tag at publish time.** Reproduced on 1.6.0 before this was written:
`mosquito/aio-pika` tag `10.2.3`, whose `pyproject.toml` says `10.0.0` and whose
`.github/workflows/publish.yml` runs `uv version "${GITHUB_REF_NAME#v}"` before publishing, gives
`tag_mismatch` (exit 1); so does a minimal repository with the same two files. The published package
has the tag's version: the file at the tag is stale on purpose. Three requirements, from the owner:

1. **Reproduced on a real project and a minimal case** (above), each kept as a proof.
2. **Static and derived are told apart by evidence in the tagged commit, never by the value.** The
   version counts as derived only when a file under `.github/workflows/` at the tagged commit has a
   step that writes the package version from the tag ref: `uv version`, `poetry version`, `hatch
   version`, `npm version` or `pnpm version` whose argument names `GITHUB_REF_NAME`, `GITHUB_REF` or
   `github.ref_name` (directly or through a variable set from them in the same file). A placeholder
   value (`0.0.0-development`, `0.0.0`) is not evidence: without such a step, the answer is unchanged.
3. **No pass without evidence.** With that evidence and a declared version that differs from the tag,
   `--tag` answers `incomplete` (exit 2), with a note naming the file and line; never `tag_matches`.
   If the declared version equals the tag, the answer stays `tag_matches`. Only `--tag` changes;
   `measure` and `--would-tag` are untouched.

Proofs before the code: D4a minimal repository with the publish step → `incomplete`, exit 2, note
names the workflow file; D4b the same without the step → `tag_mismatch`, exit 1 (unchanged); D4c
placeholder `0.0.0-development` in package.json, no step → unchanged from 1.6.0; D4d step present,
declared version equal to the tag → `tag_matches`; D4e the step's argument is a literal version, not
the ref → unchanged (`tag_mismatch`). Each of D4a must fail on 1.6.0; D4b–D4e must hold on 1.6.0 and
after. One mutant: ignore the workflow evidence; it must turn D4a red. Real case: aio-pika `10.2.3`
gives `incomplete` after the change, recorded in RECORD. Regression corpus: 99 of 99 checkable give
the recorded answer, or each difference is named here before release.

## 33. Added 2026-11-11, before any of it was written — 1.7.1

**The Action, not the detector.** An outside review of `action.yml` (release engineering) named three
points; each was checked against the code before this was written.

1. **`args` is split by the shell without quote removal, and its globs are expanded.** Confirmed: the
   step runs `$CD_ARGS` unquoted. The input documented in `action.yml` itself, `--closure 'src/**'`,
   reaches the detector as `'src/**'` with the quotes; on `mosquito/caio`, `--closure 'caio/**'` gives
   `empty_closure` (exit 2) where `--closure caio/**` on the command line gives `drift` (exit 1). With
   `allow-undetermined: true`, that drift passes. Unquoted, a glob that matches files in the working
   directory is expanded by bash before the detector sees it. `docs/CI.md` shows `--tags 'v*'`, which
   then matches no tag. From 1.7.1: `args` is split by POSIX shell word rules (quotes removed, no
   pathname expansion, no variable expansion); an unclosed quote fails the step with exit 2 and an
   error naming the input, before the detector runs.
2. **`refused` covers three different things.** Confirmed: the `verdict` output is `refused` whenever
   the JSON file does not parse. From 1.7.1 the output says which: the report's verdict; `refused`
   only for the documented refusal (exit 2, nothing on standard output), with the detector's stderr
   shown in the job summary; `error` when the exit code is not 0, 1 or 2, or standard output is not
   empty and does not parse. `error` fails the step with exit 2, also under `allow-undetermined`.
3. **The detector runs twice** (once for JSON, once for text). Confirmed. Both runs read the same
   local repository in the same step, so the two reports cannot measure different states unless the
   repository is changed by another process during the step; the cost is real. Removing it needs one
   run to write both forms, which is a change to the detector: **not in 1.7.1**; a candidate for later.

Nothing in `closure_drift.py` changes except `__version__`. Verdicts, exit codes and the report are
unchanged; `refused` and `error` are values of the Action's output, not verdicts of the report.

Proofs before the code, each run through the step's script as ACT01 does: ACT02 `args` `--closure
'src/**'` on a repository in drift → exit 1, `drift`, as the same arguments on the command line;
ACT03 a glob in `args` that matches a file in the working directory is passed unexpanded; ACT04 an
unclosed quote → exit 2, an error naming `args`, no report written; ACT05 `--tag` naming no tag →
output `verdict=refused`, exit 2, and the summary holds the detector's message; ACT06 under
`allow-undetermined: true`, a step whose run ends with output `error` still exits 2. ACT02–ACT05 must
fail on 1.7.0, ACT06 must hold on 1.7.0 or fail with the reason named here. Mutants: unquoted `$CD_ARGS`
(must turn ACT02 red); `refused` for every unparsed report (must turn ACT05 red). Regression corpus:
detector unchanged, 99 of 99 checkable as recorded.

**Amendment 1 (2026-11-11, before any code).** From the owner's review of this section:

4. **Typed inputs.** `closure` and `tags` (one glob per line), `version-file`, `version-regex`: each
   value reaches the detector as one argument, exactly as written. `args` stays for everything else,
   split as in item 1.
5. **One run.** Item 3 is taken in after all, without touching the detector: the step runs the
   detector once, with `--json`, and the log text, the annotations and the summary are all derived from
   that one report. The log names the verdict in capitals (`TAG MISMATCH`, `WOULD DRIFT`, …), the
   report's note, and the next step for that verdict (the table in `docs/USAGE.md`). The full text
   report stays the command line's.
6. **`empty_closure`, reviewed.** In the code: a closure that matches no file at every point gives
   `empty_closure` (exit 2), and at `HEAD` under `--would-tag` `empty_closure_at_head` (exit 2), never
   `clean`. A closure empty at some points only can still give `clean` on the points compared, which
   must be at least as many as those not compared. Not changed in the detector; from 1.7.1 the summary
   shows `points with empty closure` whenever it is above zero.

Proofs added before the code: ACT07 `closure: "docs dir/**"` (a path with a space) reaches the
detector as one argument, literally; ACT08 the detector is run exactly once per step; ACT09 `closure:`
matching no file → exit 2, never a pass. ACT07 and ACT08 must fail on 1.7.0; ACT09 must hold on 1.7.0
and after. A third mutant, the `closure` input ignored, must turn ACT07 red. Outside the battery, a CI
job runs the Action itself through `uses: ./` in a real workflow, on a repository it builds, with a
quoted glob and a path with a space, and fails unless the outputs are the ones required.

**Amendment 2 (2026-11-11, after the code of items 1–5, before any run in CI).** Two corrections.
(a) The second mutant, `refused` for every report that does not parse, does not touch ACT05: the case
ACT05 measures is a refusal either way. It is caught by ACT06 (a crash read as `refused`), checked on a
copy before this was written; it is registered against ACT06. (b) **1.7.1 will not be published.** By
the owner's decision, everything here is folded into one release, 1.8.0 (§34). Items 1–6 of this
section are R18-01 to R18-04 there, with these proofs and mutants.
