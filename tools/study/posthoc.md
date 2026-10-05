## A later reading of 17 reproduced collisions

**This section is not part of the study.** It is a manual reading made after run 2, it was not
pre-registered, and it enters none of the figures above. It covers 17 of the 29 repositories in
drift — those where a label in drift covers exactly two tags and no more than three labels are in
drift — and it does not represent the 29.

For each, `closure-drift --compare` was run between the two tags (2026-10-04, same detector). **All
17 reproduce**: both tags declare the same version and the compared files differ. They do not have
the same cause or the same weight:

| reading | repositories |
|---|---|
| a recent release tag whose version file was not bumped, with package code differing | 3 — `astral-sh/ruff` (`v0.0.268` declares `0.0.267`), `openai/openai-python` (`v0.26.5` declares `0.26.4`), `encode/httpcore` (`0.14.1` declares `0.14.0`) |
| the same pattern in releases from 2006–2018 | 6 — `starlette`, `psutil`, `requests`, `pygments`, `pyyaml`, `pyasn1-modules` |
| an explanation that makes the collision uninteresting to raise | 8 — no package code differs (`markupsafe`, `greenlet`); only a build script differs (`lxml`, `cffi`); maintenance-branch markers such as `3.x` (`click`, `jinja`); development markers (`numpy`); a tag named `failed-release-attempt` (`yarl`) |

Every row is in [`posthoc_17.tsv`](posthoc_17.tsv).

"Package code" here means paths outside tests, documentation, examples, scripts, CI and
configuration. It is a practical filter for deciding what is worth asking a maintainer about. It is
not a second definition of a collision and not a classification the study makes: by the study's
criterion all 17 are collisions, and they stay counted as such.
