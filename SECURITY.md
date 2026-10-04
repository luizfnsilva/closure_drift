# Security

## What this tool does to your machine

It starts `git` — `rev-parse`, `for-each-ref`, `rev-list`, `log`, `cat-file`, `config --local
--list` and `status` — against the repository you point it at, hashes what it reads, and prints a
report. When the version pattern is not one of its own (you passed `--version-regex`, or the
repository's `.closure-drift.json` names one), it also starts **itself**, once per distinct version
file, to match that pattern under a time limit; the child receives the pattern and the text on
standard input and nothing else. It starts no other program, has **no dependencies**, makes **no
network requests**, and **never writes to the repository it measures**.

### Measuring a repository you did not create

A repository can carry instructions for git in its own configuration, and a careless tool runs
them. This one is tested against the following, each a case in `tests/adversarial.py`:

- `core.fsmonitor` naming a command — overridden on every git call;
- a clean/smudge/process filter — where the repository's local config defines one, the
  working-tree check is not made and the report says `working_tree_dirty: null`, with the reason;
- `refs/replace/*` — git is run with replace objects disabled, so a tag is read as the tree it names;
- `GIT_DIR`, `GIT_WORK_TREE` and the other variables that redirect git — removed from the
  environment, so the repository measured is the one on the command line;
- hooks, `diff.*.textconv`, pagers, editors, `core.sshCommand`, aliases, `include.path`: none is
  reached by the commands above.

That list is what was tested, not a proof about every git version and every setting. If you are
handed a repository as an archive, with its `.git` directory, by someone you do not trust, the
conservative course is the usual one for any git tool: `git clone` it first — a clone does not copy
the source's configuration — and measure the clone.

The JSON report contains counts, version labels, closure hashes, the tool's own stamp, and two
paths: the repository path exactly as you passed it on the command line, and the path of your version
file. It does **not** contain file contents, and it does not list the files inside your closure
unless you ask for them with `--explain`. Look at it before you send it anywhere.

## Reporting a vulnerability

Report privately, not as a public issue:

- GitHub → **Security** → *Report a vulnerability* (private advisory), or
- `lfnsilva.invest@gmail.com`

Expect an acknowledgement within a week. This is a single-maintainer project with no service behind
it and no security team; that is the honest expectation to set rather than a policy that will not be
met.

## Verifying what you run

The citable artefact is the Zenodo deposit; every version has its own DOI. The measurement script
has had three states, and the checksum to expect depends on which deposit you pinned:

```
sha256  da5da3c0e781b67b9b3a55800d599c243edc8df649fc90b24a88e289533805c5  closure_drift.py  (0.3.0 - 0.6.0)
sha256  6d8906ef374b73e6b8c58adba813c77c4ff352f5c9c280aa43ff2baa4f804451  closure_drift.py  (0.7.0 - 0.7.1)
sha256  @@SHA@@  closure_drift.py  (0.8.0)
```

Do not take those three lines from this page as the authority: this page is inside the package it
describes, and a package does not establish its own provenance. The checksums to check against are
the ones in the `DEPOSIT.sha256` of the DOI you pinned, and the record itself:

```bash
python3 tools/verify_deposit.py --from-zenodo
```

If you script this tool, pin the version DOI and verify the checksum before executing. The author's
own working copy once drifted behind the deposited version under the same filename — the incident is
in `CHANGELOG.md`, recorded because it is the subject matter.

## Supported versions

The latest deposit is the supported one. Results from 0.7.1 and earlier on a repository whose
closure holds a non-ASCII path or a submodule pointer should be measured again with 0.8.0. Version 0.1 is superseded: it measured at every commit
unconditionally and overstates drift for any repository that publishes at tags.
