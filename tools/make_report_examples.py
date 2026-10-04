#!/usr/bin/env python3
"""Write (or check) docs/report-examples/*.json: one real report of every kind, from the detector.

    python3 tools/make_report_examples.py           # regenerate
    python3 tools/make_report_examples.py --check   # exit 1 if the committed examples are stale

The examples are produced by running the detector on tiny repositories built here with fixed
dates and identities, so they are the same bytes on every machine. They are documentation that
cannot drift from the program: CI runs --check.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DETECTOR = ROOT / "closure_drift.py"
OUT = ROOT / "docs" / "report-examples"
ENV = dict(os.environ, GIT_AUTHOR_NAME="example", GIT_AUTHOR_EMAIL="example@example.invalid",
           GIT_COMMITTER_NAME="example", GIT_COMMITTER_EMAIL="example@example.invalid",
           GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


def build(work, name, releases, head=None):
    repo = work / name
    (repo / "src").mkdir(parents=True)
    day = 0

    def git(*args):
        when = "2020-01-%02dT12:00:00+00:00" % day
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, stdin=subprocess.DEVNULL,
                       env=dict(ENV, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when))

    day = 1
    git("init", "-q")
    git("symbolic-ref", "HEAD", "refs/heads/main")
    for tag, version, code in releases + ([(None,) + head] if head else []):
        day += 1
        (repo / "VERSION").write_bytes((version + "\n").encode())
        (repo / "src" / "app.py").write_bytes(code.encode())
        git("add", "-A")
        git("commit", "-q", "-m", tag or "work after the last tag")
        if tag:
            git("tag", tag)
    return repo


def report(repo, *args):
    r = subprocess.run([sys.executable, str(DETECTOR), ".", "--json", *args], cwd=repo,
                       capture_output=True, stdin=subprocess.DEVNULL, env=ENV)
    return json.dumps(json.loads(r.stdout.decode("utf-8")), indent=1) + "\n", r.returncode


def main():
    check = "--check" in sys.argv
    work = Path(tempfile.mkdtemp(prefix="closure-drift-examples-"))
    try:
        one, two = ("v1.0.0", "1.0.0", "print('one')\n"), ("v1.1.0", "1.1.0", "print('two')\n")
        same = ("v1.0.1", "1.0.0", "print('two')\n")
        clean = build(work, "clean", [one, two])
        drift = build(work, "drift", [one, same])
        lone = build(work, "lone", [one])
        ahead = build(work, "ahead", [one], head=("1.0.0", "print('changed, version not bumped')\n"))
        bare = build(work, "untagged", [], head=("1.0.0", "print('one')\n"))
        made = {
            "clean.json": report(clean),
            "drift.json": report(drift),
            "drift-explained.json": report(drift, "--explain", "1.0.0"),
            "inconclusive.json": report(lone),
            "no_publication_points.json": report(bare),
            "would_drift.json": report(ahead, "--would-tag"),
            "would_be_clean.json": report(clean, "--would-tag"),
            "compare.json": report(drift, "--compare", "v1.0.0", "v1.0.1"),
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)
    stale = []
    if not check:
        OUT.mkdir(parents=True, exist_ok=True)
    for name, (text, code) in sorted(made.items()):
        target = OUT / name
        if check:
            if not target.exists() or target.read_bytes() != text.encode("utf-8"):
                stale.append(name)
        else:
            target.write_bytes(text.encode("utf-8"))
        print("%-28s exit %d%s" % (name, code, "   STALE" if name in stale else ""))
    if stale:
        print("\nthe committed examples differ from what the detector prints: run this script and commit.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
