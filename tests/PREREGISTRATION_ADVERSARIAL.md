# Adversarial pre-registration — closure_drift 0.8.0

Written 2026-10-04 by the independent reviewer, **before any case below was run**. The reviewer
did not write the detector and did not write `battery.py` / `negative_controls.py`.

Each attack states: **id**, **what the attacker controls and does**, and the **required outcome**
(exit code, verdict or refusal, and the property that must hold). The required outcome is derived
from the contract (PREREGISTRATION.md §1 and SCOPE/SECURITY), **independently of what the detector
actually does**. A case whose observed outcome contradicts its required outcome is reported `loose`
and is a finding; the pre-registered line is never rewritten to match a run (amendments go in §Z).

The contract under attack:
- exit 0 ⟺ verdict `clean`; exit 1 ⟺ verdict `drift`; exit 2 ⟺ no determination, cause named.
- no input produces a traceback; no failure ends at exit 1.
- never writes to the measured repository; starts no program but `git`; makes no network connection;
  does not execute commands named by the measured repository's own configuration.
- text output never carries raw control characters taken from the repository.

Terminology: a case is `as_required` when the observed outcome satisfies the required property,
`loose` when it does not (a finding), `not_run` when the platform/filesystem cannot stage it.
Every subprocess invocation of the detector is given a wall-clock time limit; exceeding it is
`loose` with the measured limit named (a hang is a finding).

Isolation for every case: `GIT_CONFIG_GLOBAL=os.devnull`, `GIT_CONFIG_NOSYSTEM=1`, a throwaway
`HOME`, and a fresh temp dir. The detector repo itself is only ever read.

---

## A. False clean / false non-drift
Goal: make two publication points carry one label over **different** closure code, yet have the
tool report anything other than `drift`.

| id | attacker controls / does | required outcome |
|---|---|---|
| AF01 | Builds a repo with two tags, same label `1.0`, whose closures genuinely differ (file `src/a.py` differs). Then adds a **git replace ref** (`refs/replace/*`) redirecting the second tag's commit (or its tree) to an object whose closure equals the first, to mask the difference. | `drift`, exit 1. The replacement must not change the measurement: the closure must reflect the tree the tag names. If the tool follows the replace ref and reports `inconclusive`/`clean`, that is a **false clean** and a finding. (Equivalently acceptable: a named refusal, exit 2 — but never 0/`clean`/`inconclusive`.) |
| AF02 | Same two-tag drift, but masks it with a **grafts** file (`.git/info/grafts`) rewriting parentage/tree. | `drift`, exit 1 (or refusal exit 2); never `clean`/`inconclusive`. |
| AF03 | Two tags, label `1.0`, identical blob content, but `src/a.py` changes mode `100644`→`100755` (becomes executable) between them. | By the declared definition closure = SHA over `(path, blob id)`, mode excluded → `inconclusive`, exit 2. Required: **not** exit 1 and **not** a crash. Reported as a *declared limit*: a mode-only change is invisible, and no doc claims otherwise — confirm the docs do not claim mode sensitivity. |
| AF04 | Two tags, label `1.0`; a regular file `src/a.py` is replaced by a **symlink** whose blob bytes equal the old file's bytes (same blob id), so `(path, id)` is unchanged though the object type/mode changed. | `inconclusive`, exit 2 (declared limit: type/mode not in the closure). Not exit 1, not a crash. Reported as a hardening gap. |
| AF05 | Two tags, label `1.0`; the only code that changes lives under an **excluded path** (`src/tests/engine.py`, matched by `**/tests/**`) that nonetheless determines output. | By design the excluded file is not in the closure → `inconclusive`, exit 2. Required: no crash. Reported as a *declared limit* and a false-clean vector when closure-determining code lives under an excluded path; also used to probe the `matches()` surprise below. |
| AF06 | Two tags, label `1.0`; the only change is a path's **case** (`src/Mod.py` ↔ `src/mod.py`), committed on a case-sensitive object store. | `drift`, exit 1 (the path string differs). |
| AF07 | Two tags, label `1.0`; the only change is a path's **Unicode normalization** (NFC `src/café.py` ↔ NFD `src/café.py`). | `drift`, exit 1 (byte-distinct paths). `not_run` where the filesystem folds them. |
| AF08 | Two tags, label `1.0`; the changing file has a name full of **glob metacharacters** (`src/[a-z]*.py`, `src/a?b.py`). | `drift`, exit 1 (the name is data, not a pattern); the file must be counted in the closure. |
| AF09 | Two tags, label `1.0`; the changing file has a **very long** path (~3000 bytes). | `drift`, exit 1; no crash. `not_run` where the filesystem refuses the length. |
| AF10 | X1 regression: two tags, label `1.0`; only `src/ação.py` (non-ASCII) changes. | `drift`, exit 1. |
| AF11 | Attempts a **hash-truncation birthday collision**: looks for two genuinely different closures in a built repo colliding to the same 16-hex value, hiding drift. | No reachable collision is expected from ordinary content; required: distinct closures observed distinct. The 64-bit truncation is reported as a hardening concern (a motivated attacker controlling content has ~2^32–2^64 work to force a masking collision; not demonstrable here). |
| AF12 | X10 regression: two tags, label `1.0`; only a **submodule pointer** under `src/` changes (same path, different recorded commit). | `drift`, exit 1 (submodule pointer is in the closure). |
| AF13 | A tag is **moved** to a different commit, or **deleted**, between two runs. | Each run reflects the current refs; no traceback; exit in {0,1,2}. (Not a false-clean by itself; included for completeness.) |
| AF14 | An **annotated tag that points at another tag object** (nested), plus a lightweight tag. | Both resolve to their commits; run completes; no crash. |
| AF15 | A tag that points at a **blob** and one that points at a **tree** (not a commit) among ordinary tags. | Run completes; those are counted in `points_not_commits`; never a crash. |

## B. False drift
Goal: reach exit 1 / `drift` without two differing closures under one label.

| id | attacker controls / does | required outcome |
|---|---|---|
| FD01 | Two tags, same label, **same content**, different commit ids (one is an amend/rebase of the other). | `inconclusive`, exit 2 — **not** `drift`. |
| FD02 | `--version-regex` with **two capture groups** both present in the version file (same label value in group 1 at every tag). | No false drift from the extra group; verdict driven by closure only. |
| FD03 | The **same repository measured twice** (determinism probe for spurious drift). | Identical verdict both runs; never a spurious `drift`. |

## C. Exit-code contract / no traceback
Every provokable failure must land on 0/1/2 with a cause, never a traceback, never 1-as-failure.

| id | attacker controls / does | required outcome |
|---|---|---|
| EC01 | Points the tool at a directory that is **not a git repo**. | refusal, exit 2. |
| EC02 | A **bare** repository (no working tree) with tags. | completes; exit in {0,2}; `working_tree_dirty` null with a note; no traceback. |
| EC03 | A repo with **no commits**. | refusal, exit 2. |
| EC04 | **Detached HEAD** at a real commit. | runs; exit per verdict; no traceback. |
| EC05 | A **tree object of a tagged commit deleted** from the object store (D14). | refusal naming git, exit 2 — never completes with that tag silently skipped. |
| EC06 | A **corrupt `.git/index`**. | no traceback; `working_tree_dirty` null (status may_fail) or verdict unaffected; exit in {0,1,2}. |
| EC07 | **HEAD points at an unborn/missing ref**. | refusal, exit 2. |
| EC08 | A repo path beginning with a **leading dash** (`-weird`). | exit 2 (argparse error or refusal); no traceback. |
| EC09 | A repo path containing **spaces and unicode**. | runs normally; exit per verdict. |
| EC10 | Caller sets **`GIT_DIR`** in the environment to a *different* (clean) repo, and points the tool's path argument at a *drifty* repo. | The tool must measure the repository named by its path argument (→ `drift`/its true verdict) **or** refuse, exit 2. It must **not** silently measure the `GIT_DIR` repo and report that repo's verdict. Misdirection is a finding. |
| EC11 | Caller sets **`GIT_WORK_TREE` / `GIT_OBJECT_DIRECTORY` / `GIT_INDEX_FILE` / `GIT_COMMON_DIR`**. | no misdirection to a different measurement without a refusal; no write outside the measured repo; no traceback; exit in {0,1,2}. |
| EC12 | `.closure-drift.json` is **`[]`** (JSON array). | refusal, exit 2. |
| EC13 | `.closure-drift.json` is **not UTF-8**. | refusal, exit 2. |
| EC14 | `.closure-drift.json` is **not JSON**. | refusal, exit 2. |
| EC15 | `.closure-drift.json` has an **unknown key** (`"closures"`). | refusal, exit 2. |
| EC16 | `.closure-drift.json` has **`"closure": "src/**"`** (a string). | refusal, exit 2. |
| EC17 | `.closure-drift.json` has **`"at": "weekly"`**. | refusal, exit 2. |
| EC18 | `.closure-drift.json` sets a **catastrophic-backtracking `version_regex`** (`(a+)+$`) with a crafted version file (`aaaa…!`) that forces exponential backtracking in `declared_version`. | The run must **terminate within the case time limit** with exit in {0,1,2}. A hang past the limit is `loose` and a finding (DoS via the measured repo's own config); the measured limit is named. The compile-probe does not bound run-time matching. |
| EC19 | `.closure-drift.json` is **deeply nested JSON** (≈100k nesting) to exhaust the parser's recursion. | refusal, exit 2 (RecursionError caught); no traceback; bounded time. |
| EC20 | `.closure-drift.json` is a **large file** (tens of MB) with an unknown key. | refusal, exit 2; bounded time. |
| EC21 | The **version file is large** (≈20 MB). | completes or refuses; exit in {0,1,2}; no traceback. |
| EC22 | The **version file is a symlink** (git blob of type symlink). | treated as blob text; no crash; exit in {0,1,2}. |
| EC23 | The **version file path is a directory / submodule** (no blob at that path). | no blob found → `no_labels`/detection refusal; exit 2; no traceback. |
| EC24 | **`--max-commits 0`** and **`--max-commits -3`**. | refusal, exit 2 (both). |
| EC25 | **`--max-commits 10**15`** (absurdly large). | runs; no crash; exit per verdict. |
| EC26 | A repo with **~1500 tags** (resolution loop stress). | completes; no crash; exit in {0,1,2}. Timing recorded (the per-tag `rev-parse` loop runs for all tags before truncation — a performance note, not a contract breach). |
| EC27 | **`--version-regex '('`** with a version file (malformed pattern). | refusal, exit 2 — not exit 1. |
| EC28 | **`--version-regex 'version'`** (no capture group) with a version file. | refusal, exit 2 — not exit 1. |
| EC29 | **`--version-regex`** given **without** any `--version-file`. | refusal, exit 2. |
| EC30 | A **repository nested inside another repository** (inner `.git`), tool pointed at the outer. | measures the outer; no crash; exit in {0,1,2}. |
| EC31 | A **linked worktree** of another repo (its `.git` is a file pointing into the main repo's `worktrees/`). | runs; no crash; no write to the main repo's object store; exit in {0,1,2}. |
| EC32 | **`PYTHONIOENCODING=ascii`** with a non-ASCII version label. | completes; no traceback (E03 parity). |
| EC33 | **stdout closed** (`1>&-`) at launch. | no traceback reaches the user; the process ends with a defined exit code; it must not crash with an uncaught exception printed to a live stderr. |
| EC34 | **SIGPIPE** — detector piped into a reader that closes early (`| head -c 1`). | no uncaught `BrokenPipeError` traceback; process ends with a defined status. |
| EC35 | The repo's **`.git` is a FILE** (`gitdir: …`) pointing at an attacker-controlled gitdir. | read-only; no command executed (see §E markers); verdict or refusal; no crash. |
| EC36 | **Dubious-ownership / `safe.directory`** interplay. | `not_run` with reason (cannot change file ownership inside a user-owned temp dir without privileges); documented. |

## D. Never writes
A byte-for-byte snapshot of the whole repository tree (including `.git`) is taken before and after;
required: **identical** (same set of paths, same bytes, same symlink targets).

| id | staged on | required |
|---|---|---|
| NW01 | a repo with a **modified, stat-dirty** tracked file, default run | repository byte-identical before/after. |
| NW02 | the same repo, `--at commits` run | byte-identical. |
| NW03 | a repo whose local config defines a `filter.*.clean` + `.gitattributes` (status path) | byte-identical (and no marker — see §E). |
| NW04 | a run that **refuses** (bad config) | byte-identical. |

## E. No command executed through the measured repository
For each, a **marker file** path in the reviewer's temp dir is handed to the configured command;
after the run the marker **must be absent**. The configured command is a tiny script that would
`touch` the marker if git ever ran it.

| id | repo-controlled setting | required |
|---|---|---|
| CX01 | `core.fsmonitor` = marker script | marker absent (overridden by `-c core.fsmonitor=false`). |
| CX02 | `core.hooksPath` → dir with executable `pre-commit`/`post-index-change`/`reference-transaction` hooks | marker absent (no write/ref op is run). |
| CX03 | `filter.x.clean` = marker script + `.gitattributes` routing a **modified** tracked file through `x` | marker absent; `working_tree_dirty` null with a note that config defines a filter. |
| CX04 | `filter.x.smudge` = marker script + `.gitattributes` | marker absent. |
| CX05 | `filter.x.process` = marker script + `.gitattributes` | marker absent. |
| CX06 | `diff.x.textconv` = marker script + `.gitattributes` | marker absent (the detector never diffs). |
| CX07 | `core.pager` = marker script | marker absent (output is captured, not a tty). |
| CX08 | `core.editor` = marker script | marker absent. |
| CX09 | `core.sshCommand` = marker script | marker absent (no fetch/push). |
| CX10 | `core.gitProxy` = marker script | marker absent. |
| CX11 | `alias.ls-tree` = `!marker script` (attempt to shadow a builtin the detector calls) | marker absent; measurement unaffected (git aliases cannot override builtins). |
| CX12 | `include.path` → a config file that defines `filter.x.clean` = marker + `.gitattributes` | marker absent; status skipped (the `include` key is seen). |
| CX13 | `includeIf.gitdir:**.path` → a config file that defines `core.fsmonitor`/`filter.x.clean` = marker | marker absent (the `includeif` key is seen; and fsmonitor is overridden regardless). |
| CX14 | `core.worktree` pointing elsewhere + `extensions.*` | no exec; no write outside the measured repo; no crash. |
| CX15 | `credential.helper` = marker script and `uploadpack.packObjectsHook` = marker | marker absent (no auth, no upload-pack). |
| CX16 | `.gitattributes` routing a path through a filter, exercised against the actual read subcommands (`ls-tree`, `cat-file blob`) | marker absent (these emit raw object bytes, not smudged). |

## F. Output injection
The attacker controls labels, tag names, commit subjects, config values, the repo-path argument,
and git's error text. Required: text output carries no raw control character taken from the repo,
no forged verdict line; JSON is always valid and round-trips the label.

| id | attacker controls / does | required |
|---|---|---|
| OI01 | A label containing a newline, an ANSI escape (`\x1b[2J`), and a forged `CLEAN: everything fine` payload. | text report: no control char but its own line ends; no line beginning `CLEAN`/`DRIFT` but the detector's own. |
| OI02 | The same label, `--json`. | valid JSON; the label value round-trips exactly (control chars as `\uXXXX`). |
| OI03 | A **tag name** with control chars / ANSI. | escaped in the text report. |
| OI04 | A **commit subject** with a newline and a fake verdict line, with `--at commits` driven to `drift` so the subject is printed in `first at …`. | escaped; no forged verdict line. |
| OI05 | A `.closure-drift.json` **unknown key** whose text holds control chars (drives a refusal that quotes it). | stderr holds no raw control char. |
| OI06 | The **repo-path argument** itself holds control chars (echoed in the header and/or a refusal). | escaped wherever printed. |
| OI07 | A label that is exactly the string **`clean`** (and one exactly `drift`). | not mistaken for a verdict; `--json` verdict field remains authoritative; text verdict lines remain the detector's own. |
| OI08 | A label with a **bidi override** (U+202E) and line/paragraph separators (U+2028/U+2029). | escaped in text; valid JSON. |

## G. The stamp
Can `detector_closure` or `measured_at_head` be made to lie?

| id | attacker controls / does | required |
|---|---|---|
| ST01 | Runs the detector via a **symlink** to `closure_drift.py`. | `detector_closure` = first 16 hex of SHA-256 of the actual source bytes executed (symlink resolves to the real file); it does not misreport. |
| ST02 | Runs via **`python -m`** from the detector's directory. | stamp = hash of that module file; honest. |
| ST03 | Runs via **`python -c "import runpy…"`** / stdin where `__file__` is absent or unreadable. | no traceback; the top-level guard yields exit 2 with the internal-error line (the stamp cannot be forged — the run fails closed instead). |
| ST04 | A **stale `.pyc`** is present for the detector. | the stamp hashes the `.py` source (`__file__`), not the `.pyc`; honest. |

## H. Closure-hash construction
The pre-image is `path‖oid` concatenated with **no separator**, digest **truncated to 16 hex**.

| id | attacker controls / does | required |
|---|---|---|
| HC01 | Two tags whose closures genuinely differ by one blob. | the two 16-hex closures differ (sanity that drift is detectable at all). |
| HC02 | Hand-constructs, in the test (not via git), two **different** `(path, oid)` entry lists whose concatenations are byte-identical, and feeds both to `closure_hash`. | the construction ambiguity is demonstrated (same digest for different logical closures) and reported as a defect of the construction (missing separator). Required classification: real construction ambiguity, **not reachable** with real git objects because oids are content-addressed and not attacker-chosen; recommend a separator / length-prefix and a full-width digest. |

---

## Coverage of the mandated checklist
- path tricks (case, unicode-normalization twins, quoting/metacharacters, very long, glob-looking, non-ASCII, non-UTF-8): AF06–AF10, C-fixtures in battery; excluded-path limit AF05.
- symlink / mode-only / type change visibility: AF03, AF04 (stated against the docs).
- submodule pointers: AF12. moved/deleted tags: AF13. annotated→tag, tag→blob/tree: AF14, AF15.
- replace refs & grafts: AF01, AF02. `.git/info/attributes`/`.gitattributes`: CX03–CX06, CX16.
- shallow clone / identical creator dates / option-looking & control-char tag names: EC-fixtures, OI03; option-looking tag names are inert because tag names are never passed to git as arguments (only objectnames are) — asserted in AF14/OI03 notes.
- unreadable/corrupt `.git`, corrupt index, missing/detached HEAD, bare, worktree, nested repo, `GIT_*` env, huge/deep/duplicate-key config, ReDoS regex, large version file, symlink/dir version file, many tags, huge `--max-commits`, dashed/space/unicode repo path, non-UTF-8/closed stdout, SIGPIPE: EC01–EC36.
- command execution vectors (fsmonitor, hooksPath, filter clean/smudge/process, textconv, pager, editor, sshCommand, gitProxy, alias, include/includeIf, extensions, worktree, credential/uploadpack, `.git`-file): CX01–CX16, EC35.
- never writes: NW01–NW04. output injection: OI01–OI08. stamp: ST01–ST04. construction: HC01–HC02.

## Z. Amendments
(none yet)

### Amendment by the maintainer, 2026-10-04, after the campaign was delivered

Nothing above is rewritten. Three notes on what happened next.

- **AF01, EC10 and EC18 were loose against the detector the campaign was written for** (commit
  `35d093a`): a replace ref masked drift, `GIT_DIR` in the caller's environment redirected the
  measurement, and a version pattern written never to finish hung the run. The detector now
  passes `--no-replace-objects`, removes the redirecting `GIT_*` variables, and matches any
  pattern that is not one of its own in a child process under a 5-second limit.
- **HC02's classification "not reachable with real git objects" does not hold.** The ambiguity
  is reachable: `src/a` (blob X) with `src/b` (blob Y), against the single file
  `src/a<X>src/b` (blob Y), hash the same bytes under the earlier construction, and both are
  ordinary trees. `tests/battery.py` proof U02 builds exactly that with real objects, checks
  that the two 16-hex values collide, and requires `drift`. The case here still demonstrates the
  ambiguity of the 16-hex value, which is kept for comparability with published closures;
  identity is decided by a second, separated, full-length hash.
- **HC01 and HC02 call `closure_hash`**, which the rewritten detector keeps under that name.
- **A harness correction, no expectation touched.** The campaign's own `git` helper inherited
  standard input, and one case calls `git hash-object --stdin` through it: run from a terminal,
  or from anything that keeps standard input open, the campaign waited there for ever. The
  helper now passes an empty standard input. Found when a run started in the background stopped
  at that call for eleven minutes.

---

## Extension, 2026-10-04 — the features of 0.9.0

Written 2026-10-04 by an independent reviewer (not the author of the detector, of `battery.py`, of
`negative_controls.py`, nor of the 85 cases above), **before any case below was run**. Nothing above
is changed. The detector under attack is `closure_drift.py` 0.9.0 on branch `release-0.8.0`.

The surface: `--would-tag`, `--tags GLOB`, `--strict`, `--explain LABEL`, `--compare A B`,
`--diagnose`, `--version`, the tag-derived-version refusal (`TAG_DERIVED`), the tag-families hint,
`--badge`/`--json` in every mode, and the tree reader (`Objects`: one `git cat-file --batch`).

The contract is the one at the top of this file, widened by PREREGISTRATION.md §7–§8 and
`docs/REPORT.md`: exit 0 only for `clean`, `would_be_clean`, `identical`,
`differs_under_two_labels`; exit 1 only for `drift`, `would_drift`, `differs_under_one_label`;
everything else exit 2 with the cause named; never a traceback; never a write to the measured
repository; no program started but `git` and the detector itself (`--match-on-stdin`); no network;
no command named by the measured repository's configuration executed; no raw control character
from the repository in text output; without `--explain`/`--compare` no path inside the closure in
the report; the `--diagnose` block carries no version label, no repository path and no path inside
the closure.

**Id prefixes.** `WT` would-tag · `TG` `--tags` · `SR` `--strict` · `XP` `--explain` · `CP`
`--compare` · `DG` `--diagnose` · `TV` tag-derived version · `TF` tag families · `MX` combinations,
`--version`, `--badge`, `--json` · `TR` tree reader. (`SR` and not `ST` for `--strict`: `ST01`–`ST04`
above already name the stamp attacks, and one id must not name two cases.)

**What "the cause named" means here.** A refusal whose stderr is the detector's own catch-all
(`internal error (…): … This is a defect in closure_drift`) has the right exit code but names no
cause in the input; where a case below says "named refusal", the catch-all does not satisfy it.

**Classification announced in advance.** Where a requirement below is not a clause of the contract
but a hardening property, the line says *(hardening)*; a loose result there is reported under
hardening, not as a contract defect. Where a behaviour is declared (README, SCOPE, SECURITY,
REPORT, §7–§8), the line says *(declared)* and requires the declaration to hold *and to be
disclosed in the report*.

Common sentinels for leak checks: label `9.8.7-LBLSENTINEL`, repository folder `REPOSENTINEL`,
closure file `src/PATHSENTINEL.py`, `HOME` folder `HOMESENTINEL`, an environment variable holding
`ENVSENTINEL`. "The diagnose block" = in text, the lines from the one starting `diagnostics` through
the one starting `  repository` (or through `  options` when the run stops before the repository
is read); in JSON, the `diagnostics` object.

Time limits: 20 s per detector invocation unless stated; 90 s where the case builds thousands of
entries or hundreds of tags. A run past its limit is `loose` (a hang).

### WT — `--would-tag`: exit 0 on a real collision?

| id | attacker controls / does | required outcome |
|---|---|---|
| WT01 | 402 tags: `v0` (label `1.0`, `src/a.py` = 1) is the oldest; 401 newer tags all point at a commit labelled `2.0`; HEAD declares `1.0` with `src/a.py` = 3. **Default** `--max-commits` (400), so `v0` falls outside the range without the user asking for a range. | **Not exit 0.** `would_drift` exit 1 (naming `v0`), or exit 2. `would_be_clean` here is a gate passing a real collision, and its text line "no existing tag declares 1.0 with different code" is false. |
| WT02 | Colliding tag `old-1.0` (label `1.0`, other code); `--tags 'v*'` on the command line excludes it. | *(declared: only matching tags are publication points)* exit 0 is acceptable **only if** the JSON reports `tags_filtered_out` ≥ 1 and the text report prints the count of tags not matching `--tags`. |
| WT03 | Colliding tag `v1` exists; `--would-tag --tags 'nothing-*'` (a glob that matches no tag). | **Not exit 0.** In the normal mode the same glob is `no_publication_points`, exit 2 (§7 T02); a gate whose selection is empty has compared HEAD with nothing and must not pass. |
| WT04 | The repository's own `.closure-drift.json` holds `"tags": ["release-*"]`; the colliding tag is `v1` (label `1.0`, other code); HEAD declares `1.0`. | *(declared)* exit 0 acceptable only if the JSON carries `tag_globs` = `["release-*"]` and `tags_filtered_out` ≥ 1, and the text prints the count of tags left out. |
| WT05 | Tag `v1` declares `1.0` but its closure is empty under the default globs (only `package.json` and `README.md`); HEAD declares `1.0` with `src/a.py`. | **Not exit 0.** The label `1.0` would name an empty closure and a non-empty one; at minimum the gate must not say "no existing tag declares 1.0 with different code" at exit 0. Exit 1 or 2. |
| WT06 | Control. Tag `v1` declares no label (no `package.json`), other code; HEAD declares `1.0`. | `would_be_clean`, exit 0, `points_without_label` = 1 in JSON. |
| WT07 | Tag `v1` declares `1.0`; HEAD declares `1.0` followed by U+200B ZERO WIDTH SPACE, other code. | *(declared: labels are compared as strings)* exit 0 `would_be_clean`; JSON `label_at_head` round-trips exactly. *(hardening)* the text line `label at HEAD` must not read exactly `1.0`: an invisible character in a label must be made visible, or the report shows the collision it says is not one. |
| WT08 | HEAD detached at a commit declaring `1.0`, other code than tag `v1` (`1.0`). | `would_drift`, exit 1, `collides_with` names `v1`. |
| WT09 | HEAD on an unborn branch (`checkout --orphan`), tags exist. | named refusal, exit 2. |
| WT10 | HEAD is already tagged `v2` (label `1.0`); older tag `v1` declares `1.0` with other code. | `would_drift`, exit 1; `collides_with` names `v1` and does not name `v2`. |
| WT11 | Tag `v1` declares `1.0` (code A); HEAD declares `1.0` (code B); a replace ref maps HEAD's commit onto `v1`'s commit to make them look identical. | `would_drift`, exit 1 (HEAD is measured as the commit it names, not its replacement). |
| WT12 | Shallow clone (`--depth 1`) of a repository whose tag `v1` declares `1.0` with other code; the ref `refs/tags/v1` is present in the clone but its commit object is not. HEAD declares `1.0`. | **Not exit 0.** A tag whose object cannot be read is a failed read (§0 X4, D14), not "a tag that does not point at a commit"; refusal exit 2 or `would_drift`. |
| WT13 | `package.json` in the working tree is changed to the colliding label `1.0` but not committed; the commit declares `2.0`. | *(declared, §7 W09)* the answer is for the commit: `would_be_clean`, exit 0, `working_tree_dirty` true, text says the commit is measured, not the working tree. |
| WT14 | A branch named `v1` exists beside the tag `v1` (label `1.0`, other code); HEAD declares `1.0`; `--would-tag --tags 'v*'`. | `would_drift`, exit 1: the tag `v1` matches `v*`. A tag left out because a branch shares its name is a false clean. |
| WT15 | Tag named `$(>MARK)v1` declares `1.0` with other code; HEAD declares `1.0`; text mode. | `would_drift`, exit 1. *(hardening)* the suggested `--compare … HEAD` line, pasted into a POSIX shell, runs nothing (the marker file is not created) and passes the tag name literally. |

### TG — `--tags GLOB`

| id | attacker controls / does | required outcome |
|---|---|---|
| TG01 | Drift repository (`v1`, `v2`, one label); `--tags '*'`. | `drift`, exit 1 (same as no `--tags`). |
| TG02 | Same; `--tags '['` (unbalanced bracket). | no traceback, not the catch-all; exit 2 `no_publication_points` (matches nothing) or exit 1 if it is read as matching; never 0. |
| TG03 | Same; `--tags '[z-a]'` (reversed range) on the command line, and the same glob as `"tags": ["[z-a]"]` in the repository's `.closure-drift.json`. | no traceback, not the catch-all; exit 2, both. |
| TG04 | Same; `--tags=-*` and `--tags -x` (leading dash). | exit 2 (argparse error or `no_publication_points`); no traceback. |
| TG05 | Same; `--tags ''` (empty string). | exit 2 (refusal or `no_publication_points`); never 0 or 1 from an empty selection. |
| TG06 | The repository's config holds `"tags": ["nomatch-*"]`, drift in `v*`. | `no_publication_points`, exit 2, the note names the glob. |
| TG07 | `py-1`, `py-2` share a label with different code (older); ten newer `rs-*` tags; `--tags 'py-*' --max-commits 2`. | `drift`, exit 1: tags are selected before the range is cut. |
| TG08 | A tag `v-tree` pointing at a tree matches `--tags 'v*'`. | counted in `points_not_commits` (≥ 1), not in `tags_filtered_out`; no crash. |
| TG09 | Drift between tags `v1` and `v2`; a branch named `v1` also exists; `--tags 'v*'`. | `drift`, exit 1. The glob is matched against tag names; a branch of the same name must not make the tag leave the selection. |

### SR — `--strict`: `clean` while some point was not compared?

| id | attacker controls / does | required outcome |
|---|---|---|
| SR01 | Two labelled tags, distinct labels; a third tag points at a tree; `--strict`. | *(declared: a tag that does not point at a commit is not a publication point)* `clean` exit 0 acceptable only with `points_not_commits` ≥ 1 in JSON and printed in text. |
| SR02 | Two labelled tags `v1`, `v2`; an unlabelled tag `x1`; `--strict --tags 'v*'`. | *(declared)* `clean` exit 0 acceptable only with `tags_filtered_out` = 1 in JSON. |
| SR03 | Shallow clone; `refs/tags/v0` present, its commit object missing; two other tags labelled and comparable; `--strict`. | **Never `clean`.** Refusal exit 2 or `incomplete` exit 2. |
| SR04 | `--strict --would-tag` and `--strict --compare A B`. | refusal, exit 2, each. |
| SR05 | `--at commits --strict`, one commit in range declares no label, no drift. | `incomplete`, exit 2. |
| SR06 | Tags `v1` (`1.0`), `v2` (`1.1`), `v3` (no label); a branch named `v3` exists; `--strict --tags 'v*'`. | **Never `clean`.** `incomplete` exit 2: `v3` matches the glob and was not compared. |

### XP — `--explain LABEL`

| id | attacker controls / does | required outcome |
|---|---|---|
| XP01 | A label `--json` in drift; `--explain=--json`. | `drift`, exit 1; `explain.label` = `--json`; the explanation lists the changed path. |
| XP02 | A label with newline, ESC, BEL, U+202E, U+2028 and a forged `CLEAN:` line in drift; `--explain LABEL` in text; and `--explain` of the same string plus `X` (not in drift). | text: no raw control character, no forged verdict line; the refusal's stderr: no raw control character. |
| XP03 | Drift where, besides `src/a.py`, also `README.md`, `docs/secret.py`, `tests/hidden_test.py` and `OUTSIDE.txt` change. | `--explain` (text and JSON) lists `src/a.py` and none of the four outside paths. |
| XP04 | One label, two tags, 5,000 changed files in the closure. | within 90 s; exit 1; JSON `changed` holds 5,000; text lists at most 40 per kind plus an "… and N more" line. |
| XP05 | One label at three tags with three different closures. | exit 1; `explain.others` has 2 entries. |
| XP06 | `--explain ''` (empty label) on a drift repository. | refusal, exit 2. |

### CP — `--compare A B`

| id | attacker controls / does | required outcome |
|---|---|---|
| CP01 | Refs that look like options: `--compare --help HEAD`; `--compare '--output=OUTFILE x' HEAD` (a space keeps argparse from reading it as an option, so it reaches git). | exit 2 each, no help text at exit 0; no file `OUTFILE` created anywhere under the case folder; repository byte-identical. |
| CP02 | Ranges: `v1..v2`, `v1...v2`. | refusal exit 2, each. |
| CP03 | Non-commit objects: `HEAD:package.json`, `HEAD^{tree}`, a raw blob id, a tag pointing at a tree. | refusal exit 2, each. |
| CP04 | The same commit twice: `v1 v1`; `v1` and its full commit id; `v1` and `v1^{}`. | `identical`, exit 0, each. |
| CP05 | A ref holding ESC, a newline and a forged `IDENTICAL:` line. | refusal exit 2; stderr carries no raw control character and no line starting `IDENTICAL`. |
| CP06 | `v1` (`1.0`, A=1), `v2` (`1.0`, A=2); a replace ref maps `v2`'s commit to `v1`'s. `--compare v1 v2`. | `differs_under_one_label`, exit 1. |
| CP07 | `v1` (`1.0`) and an orphan branch with no common history declaring `1.0` with other code. | `differs_under_one_label`, exit 1. |
| CP08 | Same label; besides `src/a.py`, `README.md`, `docs/secret.py`, `tests/hidden_test.py`, `OUTSIDE.txt` change. | text and JSON list `src/a.py` and none of the four outside paths. |
| CP09 | `v1` declares `1.0`, `v2` declares `1.0` followed by U+00A0 NO-BREAK SPACE, other code. | *(declared)* `differs_under_two_labels`, exit 0, labels round-trip in JSON. *(hardening)* in text the two `label` lines must differ visibly (not render identically). |

### DG — `--diagnose`

| id | attacker controls / does | required outcome |
|---|---|---|
| DG01 | Drift repository in folder `REPOSENTINEL`, label `9.8.7-LBLSENTINEL`, closure file `src/PATHSENTINEL.py`, `HOME` under `HOMESENTINEL`, an env var `= ENVSENTINEL`; absolute repo path; text and `--json`. | the diagnose block contains none of the five sentinels. |
| DG02 | Same, the repository passed as a relative path (`REPOSENTINEL`) from its parent folder. | no sentinel in the block (text and JSON). |
| DG03 | Same, with `--closure 'src/PATHSENTINEL.py'` (a glob that is a literal path inside the closure). | the diagnose block does not contain `PATHSENTINEL`. |
| DG04 | Same, with `--tags 'v9.8.7-LBLSENTINEL*'` (a tag glob carrying the version label). | the diagnose block does not contain `LBLSENTINEL`. |
| DG05 | Same, with `--explain 9.8.7-LBLSENTINEL`, `--version-file package.json --version-regex '"version": "(9[^"]*LBLSENTINEL)"'`, and separately `--compare` of two refs named `REFSENTINEL-a`, `REFSENTINEL-b`. | the block carries only booleans for them: no `LBLSENTINEL`, no `REFSENTINEL`. |
| DG06 | Drift, clean, `would_drift`, `would_be_clean`, `--compare` (one label), `no_publication_points`: each run with and without `--diagnose --json`. | identical exit codes; JSON identical apart from the `diagnostics` key. |
| DG07 | `--diagnose` on a repository whose config sets `core.fsmonitor`, `core.hooksPath` hooks, a clean filter, and a promisor remote whose `uploadpack` is a marker script; run with the repository as cwd and `.` as argument. | marker absent; repository byte-identical. |
| DG08 | `--diagnose` (text) and `--diagnose --json` on a folder `REPOSENTINEL` that is not a repository. | exit 2; text: the block is printed and holds no `REPOSENTINEL`; JSON: stdout empty. |
| DG09 | `--diagnose --json` on a drift repository. | `diagnostics` holds exactly the keys of REPORT.md (`detector_version`, `detector_closure`, `python`, `platform`, `git`, `options`, `repository`) and `detector_version` equals `__version__` in the file. |

### TV — the tag-derived-version refusal

| id | attacker controls / does | required outcome |
|---|---|---|
| TV01 | No version file; `pyproject.toml` lists a dependency `pbrt-tools` (the substring `pbr`). | refusal exit 2, whose text tells the user `--version-file`. |
| TV02 | No recognised version file; `pyproject.toml` holds the comment `# we do not use setuptools_scm`; the version is in `src/pkg/__init__.py` (`__version__ = "1.0"`) with no `dynamic`. | exit 2. *(hardening)* the refusal must not state that the version is derived from the tag: no tag-deriving tool is configured, and the repository is measurable with `--version-file`. |
| TV03 | `package.json` declares the label (drift), and `pyproject.toml` names `setuptools_scm`. | measured: `drift`, exit 1. |
| TV04 | `setup.py` with `import versioneer` and `version=versioneer.get_version()`, no other version file. | refusal exit 2 naming `versioneer`. |

### TF — tag-families hint

| id | attacker controls / does | required outcome |
|---|---|---|
| TF01 | Drift between tags `x'$(>MARK)-1.0` and `y-1.0` (two families), text mode. | `drift`, exit 1. *(hardening)* the suggested `--tags …` argument, evaluated by a POSIX shell, runs nothing (marker absent) and yields the literal prefix followed by `*`. |
| TF02 | Drift between tags `1.0` (empty prefix) and `py-1.0`. | `drift`, exit 1; `tag_families` has keys `""` and `py-`; text prints `(none)` and suggests `--tags 'py-*'`. |
| TF03 | 300 tags `f000-1` … `f299-1`, one label, 300 different closures. | within 90 s; `drift`, exit 1; `tag_families` has 300 keys; no traceback. |
| TF04 | Drift between tags `‮abc-1.0` and `py-1.0` (a bidi override in a family prefix). | text: no raw U+202E. |

### MX — `--version`, `--badge`, `--json`, `--help` across modes

| id | attacker controls / does | required outcome |
|---|---|---|
| MX01 | `--version` together with `--json --badge --diagnose --would-tag --max-commits 0`, and with `--compare a b`. | stdout exactly `closure_drift <__version__>` and a line end; exit 0; stderr empty. |
| MX02 | `--badge` with `--would-tag` (collision), `--compare` (one label), `--explain` (drift), `--strict` (incomplete). | stdout exactly one line, a badge naming that verdict and the 12-hex HEAD; exit 1, 1, 1, 2. |
| MX03 | `--json` in each mode: normal (drift), `--explain`, `--would-tag`, `--would-tag --tags`, `--compare`, `no_publication_points`, `--diagnose`. | valid JSON; every field REPORT.md lists for that kind is present with its documented type. |
| MX04 | `--diagnose --badge`; `--json --badge`. | refusal exit 2, stdout empty. |
| MX05 | `--help` and `-h`. | *(literal contract)* not exit 0: exit 0 is reserved for the four verdicts. If exit 0, classified as a documentation/contract-wording gap, not a measurement defect. |

### TR — the tree reader (`git cat-file --batch`)

| id | attacker controls / does | required outcome |
|---|---|---|
| TR01 | One folder of 5,000 files in the closure; three tags under one label; one file changes. | within 90 s; `drift`, exit 1. |
| TR02 | A file 200 folders deep under `src/` changes under one label. | within 90 s; `drift`, exit 1. |
| TR03 | A tree entry named `a\nCLEAN: forged.py` under `src/` changes under one label (built with `fast-import`); `--explain 1.0` in text. | `drift`, exit 1; no raw newline inside a printed path; no forged `CLEAN` line. |
| TR04 | A tree entry whose name is the bytes `\xff\xfe.py` under `src/` changes under one label; `--json --explain 1.0`. | `drift`, exit 1; valid JSON; text has no traceback. |
| TR05 | A tagged commit whose root tree object is corrupt (bytes with no entry structure, written with `hash-object --literally`). | named refusal, exit 2 — not the catch-all, not a traceback, never 0. |
| TR06 | The version-file blob at an older tag is deleted from the object store. | refusal exit 2; never `clean`. |
| TR07 | `git cat-file --batch` dies after answering two requests (a `git` wrapper on `PATH` that proxies to the real git). | named refusal exit 2 within 20 s — no hang, not the catch-all, no traceback. |
| TR08 | A `--object-format=sha256` repository: drift; `--compare` of the two tags; `--would-tag` with a colliding HEAD. | exit 1 each, verdicts `drift`, `differs_under_one_label`, `would_drift`. `not_run` where git cannot create one. |
| TR09 | A tagged commit whose root tree ends with a truncated entry (the last object id cut to 10 bytes). | exit 2, no traceback; never 0. |
| TR10 | A partial clone: `extensions.partialClone=origin`, `remote.origin.promisor=true`, `remote.origin.url` a local `file://` folder, `remote.origin.uploadpack` a marker script; the version-file blob at a tag is missing. | marker absent (no command named by the repository's config runs through a lazy fetch); repository byte-identical; exit 2 or a determination, no traceback. |

### Amendments to this extension

Written 2026-10-04, after the first full run of the extension (python 3.14). No line above is
changed; no expectation in `tests/adversarial.py` is changed.

- **TF03 — the reviewer's expectation was wrong.** The tags were named `f000-1` … `f299-1`. The
  family of a tag is everything before its first digit (optionally preceded by `v`), so all 300
  tags are one family, `f`, and the detector is right to report one. TF03 stays in the campaign as
  pre-registered and stays `loose`; it is **not a finding**. To measure what TF03 meant to measure,
  one case is added after the run and marked as such:

  | id | attacker controls / does | required outcome |
  |---|---|---|
  | TF05 *(added after the first run)* | 300 tags whose prefixes are 300 distinct letter strings (`faaa-1`, `faab-1`, …), one label, 300 different closures. | within 90 s; `drift`, exit 1; `tag_families` has 300 keys; the text run completes without a traceback. |

- **XP03 and CP08 — loose, but not for the reason the line anticipated.** `--explain` and
  `--compare` do not list a path outside the closure the detector computed: they list
  `docs/secret.py`, and the detector computes it **inside** the closure. The cause is
  `matches()` with the exclusions `**/docs/**`, `**/tests/**`, `**/test/**`, `**/spec/**`,
  `**/vendor/**`, `**/node_modules/**`: each needs at least one folder before the excluded one, so a
  `docs/` or `tests/` folder **at the repository root** is not excluded, and `*.py` brings its
  files in. SCOPE.md declares those folders "outside every closure". Measured by hand on the same
  detector: two tags, one label, only `tests/conftest.py` at the root changed → `drift`, exit 1, and
  `--explain` lists `tests/conftest.py`. The line's requirement (none of the four outside paths
  listed) stands and is not met; the defect is in the closure definition, not in `--explain` or
  `--compare`. (`tests/hidden_test.py` and `README.md` are excluded, by `**/*_test.*` and
  `**/*.md`; `OUTSIDE.txt` matches no include glob.)
- **TG03 differs by interpreter.** Under CPython 3.14 it is `as_required`; under CPython 3.9.6 it is
  `loose`: there `fnmatch` compiles `[z-a]` to a regular expression with a reversed range and
  raises `re.error`, which reaches the detector's catch-all (`internal error (error)`, exit 2).
  The same pattern reaches `fnmatch` through `--closure` and the config's `closure`. Exit code right,
  cause not named — a finding on 3.9 only.
