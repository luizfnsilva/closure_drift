# Security

## What this tool does to your machine

It starts `git` (`--version`, `rev-parse`, `for-each-ref`, `rev-list`, `log`, `cat-file`,
`config --local --list`, `status`) and, for a version pattern that is not built in, itself — to match
that pattern under a time limit. Nothing else. No dependencies, no network, and it never writes to
the repository it measures.

A repository's own git configuration can name commands. These are blocked, and each is a case in
`tests/adversarial.py` with a positive control (plain git does run the command on the same
repository):

- `core.fsmonitor`
- clean / smudge / process filters (the working-tree check is skipped and reported as `null`)
- `refs/replace/*`
- the lazy fetch of a partial clone (refused on git older than 2.45, which cannot disable it)
- `GIT_DIR`, `GIT_WORK_TREE` and similar variables in your environment

Hooks, pagers, editors, `textconv`, `core.sshCommand` and aliases are not reached by the commands
above. This is what was tested, not a proof about every git version. For a repository received as
an archive from someone you do not trust, `git clone` it first and measure the clone.

The JSON report holds counts, labels, hashes, the repository path as you typed it and the path of
the version file. No file contents, and no path inside the closure unless you pass `--explain` or
`--compare`.

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
sha256  1125e51615efc3698f09e7bce92bc8647eb468db5471ca79b8ee202cef684cda  closure_drift.py  (0.9.0)
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
closure holds a non-ASCII path or a submodule pointer should be measured again with 0.9.0. Version 0.1 is superseded: it measured at every commit
unconditionally and overstates drift for any repository that publishes at tags.
