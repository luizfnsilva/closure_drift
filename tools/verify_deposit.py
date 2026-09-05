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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "DEPOSIT.sha256"
RECORD_API = "https://zenodo.org/api/records/22283946"


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


def check_zenodo() -> bool:
    import json
    import urllib.request

    with urllib.request.urlopen(RECORD_API, timeout=30) as response:
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
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-zenodo", action="store_true",
                        help="also download the record and compare it to the manifest")
    args = parser.parse_args()

    ok = check_local()
    if args.from_zenodo:
        ok = check_zenodo() and ok
    print("\ndeposit verified" if ok else "\nDEPOSIT VERIFICATION FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
