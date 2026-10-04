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

