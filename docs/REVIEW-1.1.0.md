# Review of the 1.1.0 candidate, as delivered

An adversarial reviewer who did not write §16.1–16.5 attacked the candidate (`release-1.1.0` at
`cc88631`) on 2026-10-09, before any tag. The findings are kept here as delivered, before any fix;
what was done about each is in `tests/PREREGISTRATION.md`, §16 amendment 3.

| id | kind | finding |
|---|---|---|
| R1 | wrong 0 | a UTF-8 BOM on the first line of the `--published` file makes that line a version no tag matches; a real drift on `1.0.0` becomes `clean` |
| R2 | wrong 0 | a line that is not a version (`1.0.0  # first release`, `1.0.0 1.0.1`) is accepted and matches nothing; the same drift disappears |
| R3 | wrong 1 | tags not on the list are included: `tag_label` keeps only the last number of `nightly-2024-02-01` (`01`, key `1`) and of `build-1`, which then match a list line `1.0` |
| R4 | wrong 1 (opt-in) | `version_key` drops trailing `.0` after a pre-release part: `1.0.0-rc.0` = `1.0.0-rc`; and `1.0-rc` ≠ `1.0.0-rc` although `1.0` = `1.0.0` |
| R5 | inconsistency | with `--label-equality version` the report names a label no file declares (`1`), and `--explain 1.0` is refused |
| R6 | wrong 1 | a commented-out `# spec.version = "0.1.0"` in a gemspec is read as the version |
| R7 | wrong 1 | when the shallowest `lib/**/version.rb` gives no plain string, a deeper, vendored one is read (`lib/foo/vendor/thor/version.rb`) |
| R8 | wrong 1 | with `go.mod`, `tag_label` drops `v` and prefixes: `1.0.0` and `v1.0.0`, or `server-v1.0.0` and `cli-v1.0.0`, become one label; a Go module's version is the whole tag. 1.0.0 refused these repositories |
| R9 | inconsistency | `--at commits` results change with no new option: build-number tags contradict a correct file, and real drift becomes `incomplete`; §16's preamble says no result changes without a new option |
| R10 | inconsistency | the `--at commits` vote reads every tag's full tree: a damaged object under a tag outside HEAD's history now refuses a run that 1.0.0 answered |
| R11 | wrong 0 | `--would-tag` with a list that leaves out every tag answers `would_be_clean` over nothing; `--tags` in the same case refuses |
| R12 | wrong 1 | with the honest full list (the helper's `0.1.0` was a real release), the ZA04 helper file agrees at every tag again: "on the list" does not depend on which tag the label is read at |
| R13 | doc | `tags_included` counts before `--max-commits`; listed tags that point at no commit are in neither count; the no-points note does not mention `--tags` when both filter |

Attacks that held: unreadable, empty, directory, UTF-16 and comment-only lists are refused by
name; CRLF works; `--published` is refused with `--at commits`, `--compare` and components;
no wrong early refusal (16.3) in any case tried; `--modes` on a symlink and on a non-UTF-8 name;
`1.10`/`1.1`, `v2`/`2.0.0-beta`, `1.0.0+0`/`1.0.0` kept apart; the badge; no traceback; 17 local
repositories gave the same verdict, labels, points and version file under 1.1.0 and 1.0.0 with no
option, `--at commits` and `--would-tag`.
