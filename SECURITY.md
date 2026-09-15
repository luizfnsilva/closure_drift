# Security

## What this tool does to your machine

It runs `git log`, `git show` and `git ls-files` against a repository you point it at, hashes the
bytes it reads, and prints a report. It has **no dependencies**, makes **no network requests**, and
**never writes to the repository it measures**. It is a single file you can read in one sitting, and
reading it before running it is encouraged.

The JSON report contains counts, version labels, closure hashes, the tool's own stamp, and two
paths: the repository path exactly as you passed it on the command line, and the path of your version
file. It does **not** contain file contents, and it does not list the files inside your closure. Look
at it before you send it anywhere.

## Reporting a vulnerability

Report privately, not as a public issue:

- GitHub → **Security** → *Report a vulnerability* (private advisory), or
- `lfnsilva.invest@gmail.com`

Expect an acknowledgement within a week. This is a single-maintainer project with no service behind
it and no security team; that is the honest expectation to set rather than a policy that will not be
met.

## Verifying what you run

The citable artefact is the Zenodo deposit; every version has its own DOI. The measurement script
has had two states, and the checksum to expect depends on which deposit you pinned:

```
sha256  da5da3c0e781b67b9b3a55800d599c243edc8df649fc90b24a88e289533805c5  closure_drift.py  (0.3.0 - 0.6.0)
sha256  6d8906ef374b73e6b8c58adba813c77c4ff352f5c9c280aa43ff2baa4f804451  closure_drift.py  (0.7.0 onward)
```

Do not take those two lines from this page as the authority: this page is inside the package it
describes, and a package does not establish its own provenance. The checksums to check against are
the ones in the `DEPOSIT.sha256` of the DOI you pinned, and the record itself:

```bash
python3 tools/verify_deposit.py --from-zenodo
```

If you script this tool, pin the version DOI and verify the checksum before executing. The author's
own working copy once drifted behind the deposited version under the same filename — the incident is
in `CHANGELOG.md`, recorded because it is the subject matter.

## Supported versions

The latest deposit is the supported one. Version 0.1 is superseded: it measured at every commit
unconditionally and overstates drift for any repository that publishes at tags.
