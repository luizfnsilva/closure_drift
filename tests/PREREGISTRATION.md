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
