---
name: closure-drift
license: Apache-2.0
description: Use before creating a git tag, cutting a release, bumping a version, or publishing a package (PyPI, npm, crates, a deploy), and when asked which code a version number names. Checks that the version label does not already name different code in the repository's tags.
---

# closure-drift

A version label (`1.4.2`) should name one state of the code. When a release is tagged without
bumping the version, the same label names two different things, and nothing else notices.
closure_drift checks that. It is read-only: it runs git reads on the local repository, no network.

## When to run it

- Before `git tag`, `gh release create`, `npm publish`, `twine upload`, `cargo publish`, or any
  release or deploy step that names a version.
- After changing the file that declares the version, before tagging it.
- When asked "what code is version X?" or "why do two releases with the same version differ?".

Not needed for work that does not create or name a release: editing code, running tests,
refactoring, a commit without a tag, a branch, a pull request. Do not run it there.

## How

If the MCP tool `would_tag` is available, call it with the repository path. Otherwise:

```bash
python3 closure_drift.py --would-tag --json .
```

Without the script: `curl -sO https://raw.githubusercontent.com/luizfnsilva/closure_drift/main/closure_drift.py`,
or `uvx --from git+https://github.com/luizfnsilva/closure_drift closure-drift --would-tag --json .`

## What the answer means, and what to do

| exit | verdict | do |
|---|---|---|
| 0 | `would_be_clean` | Tag. |
| 1 | `would_drift` | Do not tag. The label at HEAD already names other code. Tell the person, propose a version, and wait: change the version file only to the version they agree to, then commit and run the check again. |
| 2 | anything else, or a refusal | Exit 2 is not a pass. Nothing was decided. Read the reason in the output and show it to the person. Do not tag on your own. |

Common reasons for exit 2:

- No label found: pass `--version-file` with the file that declares the version. If the
  refusal names a `package.json` marked private, and the project is released by deploying,
  `--version-file package.json` is right.
- A file over the size limit was not read, or few tags could be compared: report it as is.
- No tags yet: `--would-tag` still answers; a full measurement needs two releases.

To audit the whole history instead of one tag: `python3 closure_drift.py --json .` (exit 1 means a
label names more than one state; `--explain LABEL` lists the paths that differ).

## Never

- Never delete, move or re-point a published tag to make the check pass. Other people and package
  indexes already point at it. Bump the version instead.
- Never edit the version file only to silence the check without the person agreeing to that
  version. Changing tags or history needs the person's explicit authorization.
- Never report "checked" when the exit code was 2, or when you could not run the check at all
  (no Python, no script, no tags fetched): say plainly that it was not done.

## What this skill is not

It reminds you to check and tells you how to read the answer. The CI gate (`docs/CI.md`) is what
blocks a release when the check was skipped. It cannot see which commit a registry package was
built from; it reads git only.
