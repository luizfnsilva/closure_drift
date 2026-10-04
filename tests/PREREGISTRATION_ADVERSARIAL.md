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
