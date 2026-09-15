#!/usr/bin/env python3
"""Verify that the nine deposited files in this repository are byte-identical to the Zenodo deposit.

The deposit is the citable artefact; this repository is where it is developed and where results are
collected. If the two ever disagree, a measurement citing the DOI cannot be checked against the code
that produced it — which is the failure this tool exists to detect, occurring in its own repository.

  python3 tools/verify_deposit.py              # check against DEPOSIT.sha256 (offline, no network)
  python3 tools/verify_deposit.py --from-zenodo  # also re-fetch the record and compare (needs network)

Exit code 0 if every file matches, 1 otherwise. Zero dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "DEPOSIT.sha256"
RECORD_API = "https://zenodo.org/api/records/%s"


def record_id() -> str:
    """The record to compare against, read from the manifest — never hard-coded here.

    A number written in this file goes stale the moment a new version is deposited, and it went
    stale exactly that way: it named the 0.6.0 record while the repository held 0.7.x, so
    --from-zenodo reported MISMATCH on three files that were not wrong. The manifest's own header
    names the version DOI of the deposit it describes, and that is the only right answer.
    """
    texto = MANIFEST.read_text(encoding="utf-8")
    m = re.search(r"Version DOI\s+10\.5281/zenodo\.(\d+)", texto)
    if not m:
        print("DEPOSIT.sha256 does not name a version DOI yet: this version has not been "
              "deposited, so there is no record to compare against.", file=sys.stderr)
        print("Pass --record <id> to compare against a specific record anyway.", file=sys.stderr)
        raise SystemExit(2)
    return m.group(1)


def read_manifest() -> list[tuple[str, str]]:
    entries = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, _, path = line.partition("  ")
        entries.append((digest, path))
    return entries


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_local() -> bool:
    ok = True
    for want, rel in read_manifest():
        target = ROOT / rel
        if not target.exists():
            print(f"MISSING   {rel}")
            ok = False
            continue
        got = sha256(target)
        if got == want:
            print(f"ok        {rel}")
        else:
            print(f"MISMATCH  {rel}\n          expected {want}\n          got      {got}")
            ok = False
    return ok


def check_zenodo(rec_id: str) -> bool:
    import json
    import urllib.request

    with urllib.request.urlopen(RECORD_API % rec_id, timeout=30) as response:
        record = json.load(response)
    print(f"\nrecord    {record['doi']}  (version {record['metadata']['version']})")
    manifest = {rel.split("/")[-1]: want for want, rel in read_manifest()}
    ok = True
    for entry in record["files"]:
        key = entry["key"]
        with urllib.request.urlopen(entry["links"]["self"], timeout=60) as response:
            data = response.read()
        got = hashlib.sha256(data).hexdigest()
        want = manifest.get(key)
        if want is None:
            print(f"UNLISTED  {key} is in the record but not in DEPOSIT.sha256")
            ok = False
        elif got == want:
            print(f"ok        {key}")
        else:
            print(f"MISMATCH  {key} differs from the manifest")
            ok = False

    # The symmetric half, which was missing: a file listed in the manifest and absent from the
    # record is as much a divergence as one present and different, and it is the half that a
    # rename would produce.
    faltando = set(manifest) - {entry["key"] for entry in record["files"]}
    for key in sorted(faltando):
        print(f"MISSING   {key} is in DEPOSIT.sha256 but not in the record")
        ok = False
    if len(record["files"]) != len(manifest):
        print(f"COUNT     the record carries {len(record['files'])} files, "
              f"the manifest lists {len(manifest)}")
        ok = False
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-zenodo", action="store_true",
                        help="also download the record and compare it to the manifest")
    parser.add_argument("--record", metavar="ID",
                        help="record id to compare against (default: the one named in DEPOSIT.sha256)")
    args = parser.parse_args()

    ok = check_local()
    if args.from_zenodo:
        ok = check_zenodo(args.record or record_id()) and ok
    print("\ndeposit verified" if ok else "\nDEPOSIT VERIFICATION FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
