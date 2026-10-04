#!/usr/bin/env python3
"""Build tools/study/selection.tsv by the rule fixed in tools/study/PREREGISTRATION.md.

    python3 tools/study/build_selection.py

Network: one ranking file and one PyPI metadata request per project walked. Standard library only.
The output is committed before any repository in it is measured.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

RANKING = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"
PYPI = "https://pypi.org/pypi/%s/json"
GITHUB = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
WANTED = 100
OUT = Path(__file__).resolve().parent / "selection.tsv"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "closure_drift-study"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def github_repo(info):
    urls = list((info.get("project_urls") or {}).values()) + [info.get("home_page") or ""]
    for url in urls:
        m = GITHUB.search(url or "")
        if m and m.group(1).lower() not in ("sponsors", "orgs", "users"):
            repo = m.group(2)
            if repo.endswith(".git"):
                repo = repo[:-4]
            return "%s/%s" % (m.group(1), repo)
    return None


def main():
    ranking = fetch(RANKING)
    rows, seen = [], {}
    selected = 0
    for rank, row in enumerate(ranking["rows"], start=1):
        if selected >= WANTED:
            break
        name = row["project"]
        try:
            repo = github_repo(fetch(PYPI % name)["info"])
        except Exception as e:  # noqa: BLE001 — recorded, not hidden
            rows.append((rank, name, "", "metadata_unavailable:%s" % type(e).__name__))
            continue
        if repo is None:
            rows.append((rank, name, "", "no_github_url"))
        elif repo.lower() in seen:
            rows.append((rank, name, repo, "same_repository_as:%s" % seen[repo.lower()]))
        else:
            seen[repo.lower()] = name
            selected += 1
            rows.append((rank, name, repo, "selected"))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# ranking: %s\n# last_update: %s\n" % (RANKING, ranking.get("last_update")))
        fh.write("# rank\tproject\trepository\tstatus\n")
        for r in rows:
            fh.write("%d\t%s\t%s\t%s\n" % r)
    print("%d projects walked, %d repositories selected -> %s" % (len(rows), selected, OUT))
    return 0 if selected == WANTED else 1


if __name__ == "__main__":
    sys.exit(main())
