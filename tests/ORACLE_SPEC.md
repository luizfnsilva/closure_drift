# Specification for an independent oracle

Written 2026-10-05, before the oracle and before any comparison with the detector.

`tests/oracle.py` computes, from this page alone, what `closure_drift.py` should answer in the one
mode where nothing is a heuristic: the version file and its pattern are given. Whoever writes it
does not read `closure_drift.py` nor anything else under `tests/`. It talks to git through
`git ls-tree -r -z --full-tree`, `git for-each-ref`, `git rev-parse` and `git cat-file blob` only,
with `--no-replace-objects`. Python 3.9+, standard library only.

## 1. Entries of a commit

Every line of `git ls-tree -r -z --full-tree <commit>`: mode, type, object id, path (bytes).
Kept: type `blob` (any mode, symbolic links included) and type `commit` (a submodule pointer).
Order: the order git prints.

## 2. Glob language

Matching is on the whole path, case-sensitive on every platform, with `/` an ordinary character:

- `*` any run of characters, empty included, `/` included; `**` means the same as `*`
- `?` exactly one character, `/` included
- `[seq]` one character in `seq`; `[!seq]` one character not in it; ranges `a-z`; a `]` first in
  the set is literal; a `[` with no closing `]` is a literal `[`
- anything else is itself

A path matches a glob `g` when any of these holds:

1. the path matches `g`;
2. `g` starts with `**/` and the path matches `g` without those three characters;
3. `g` ends with `/**` and the path starts with the text of `g` without its last three
   characters, followed by `/` — compared as plain text, not as a pattern.

Paths are matched as text decoded from UTF-8 with `surrogateescape`.

## 3. Closure

Include globs: given with `--closure` (repeatable); otherwise
`src/**  lib/**  app/**  *.py  *.js  *.ts  *.rs  *.go  *.java`.

Exclude globs, always: `**/test/**  **/tests/**  **/*_test.*  **/*.test.*  **/spec/**  **/docs/**
**/*.md  **/node_modules/**  **/vendor/**  **/.git/**`.

An entry is a member when its path matches an include glob and no exclude glob.

- **full id**: SHA-256, hex, over the members in order, each as
  `path bytes` `NUL` `type` `SP` `object id in hex` `LF`
- **short id**: the first 16 hex characters of SHA-256 over the members in order, each as
  `path bytes` followed by `object id in hex`, nothing between
- **files**: the number of members

## 4. Publication points

Every ref under `refs/tags/` that peels to a commit (`<object>^{commit}`), named without the
`refs/tags/` prefix. A tag that does not peel to a commit is counted in `points_not_commits`.
With `--tags GLOB` (repeatable) only tags whose name matches a glob are points — here with
Python's `fnmatch.fnmatchcase` — and the others are counted in `tags_filtered_out`.

## 5. Label

The version file is a path; the pattern is a Python regular expression with one capture group.
At a point: the entry of type `blob` whose path equals the version file, its bytes decoded as
UTF-8 with `errors="replace"`, `re.search(pattern, text, re.MULTILINE)`, group 1. No such entry,
no match, or an empty capture: the point has no label.

## 6. A full run

For each point: if the closure has no member the point is *empty* (its label is not read).
Otherwise, with a label it is *compared*; without one it is *without label*.

Verdict, first rule that applies:

| rule | verdict | exit |
|---|---|---|
| some label was seen with two or more different full ids | `drift` | 1 |
| every point is empty | `empty_closure` | 2 |
| no point has a label | `no_labels` | 2 |
| exactly one distinct label | `inconclusive` | 2 |
| `--strict`, and some point is empty or without label | `incomplete` | 2 |
| otherwise | `clean` | 0 |

No points at all: verdict `no_publication_points`, exit 2.

Output of `oracle.py REPO --version-file F --version-regex R [--closure G]... [--tags G]... [--strict]`,
one JSON object: `verdict`, `exit`, `labels` (distinct labels), `labels_covering_multiple_closures`,
`max_closures_per_label`, `publication_points_scanned`, `publication_points_compared`,
`points_without_label`, `points_with_empty_closure`, `points_not_commits`, `tags_filtered_out`,
`drifting` (object: label → sorted list of full ids), `points` (object: tag name →
`{"commit", "label", "closure_id", "closure", "files"}`; the three last are `null`/0 when empty).

## 7. Two references

`oracle.py REPO --compare A B [--closure G]...`: each reference is read as `refs/tags/<name>` if
that peels to a commit, else as any revision. One JSON object: `a` and `b`
(`{"commit", "closure_id", "closure", "files"}`), `changed` (members of both whose type or object
id differ), `only_in_a`, `only_in_b` — three sorted lists of paths, decoded with `surrogateescape`
and sorted as Python strings.

## 8. Its own check

`oracle.py --self-test` builds a few small repositories and checks the oracle against values
worked out by hand in the test itself. It never calls `closure_drift.py`.
