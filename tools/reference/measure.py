#!/usr/bin/env python3
"""Measure the six reference repositories with this detector and write tools/reference/*.json.

    python3 tools/reference/measure.py CLONES_DIR      # CLONES_DIR holds click.git, requests.git, …

Each file holds the repository's HEAD, the command, the exit code and the report as emitted, at
the default range and at every tag. README's reference table is read from these files.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DETECTOR = HERE.parent.parent / "closure_drift.py"
REPOS = {"pallets/click": "click", "psf/requests": "requests", "pypa/packaging": "packaging",
         "encode/httpx": "httpx", "impress/impress.js": "impress.js", "lodash/lodash": "lodash"}


def main():
    clones = Path(sys.argv[1])
    for slug, name in REPOS.items():
        clone = clones / (name + ".git")
        head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True,
                              text=True).stdout.strip()
        row = {"repository": slug, "head": head, "runs": {}}
        for key, extra in (("default", []), ("every_tag", ["--max-commits", "1000000"])):
            r = subprocess.run([sys.executable, str(DETECTOR), str(clone), "--json", *extra],
                               capture_output=True, stdin=subprocess.DEVNULL)
            report = json.loads(r.stdout.decode("utf-8"))
            report["repo"] = slug
            row["runs"][key] = {"args": extra, "exit": r.returncode, "report": report}
        (HERE / (name + ".json")).write_text(json.dumps(row, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        e = row["runs"]["every_tag"]["report"]
        print("%-22s %-9s %s of %s labels in drift; %s of %s tags compared" % (
            slug, e["verdict"], e["labels_covering_multiple_closures"], e["labels"],
            e["publication_points_compared"], e["publication_points_scanned"]))


if __name__ == "__main__":
    main()
