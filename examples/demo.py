#!/usr/bin/env python3
"""See the three answers in one minute, on three tiny repositories built in front of you.

    python3 examples/demo.py

Nothing is downloaded and nothing outside a temporary folder is touched. Each repository has a
`VERSION` file, one source file and two tags. The script prints what it did, what closure_drift
answered, and what it should have answered; it exits 0 only if the three match.
Needs CPython 3.9+ and git.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DETECTOR = HERE.parent / "closure_drift.py"
ENV = dict(os.environ, GIT_AUTHOR_NAME="demo", GIT_AUTHOR_EMAIL="demo@example.invalid",
           GIT_COMMITTER_NAME="demo", GIT_COMMITTER_EMAIL="demo@example.invalid",
           GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

CASES = [
    ("clean",
     "Two releases. The version was bumped, and the code changed.",
     [("v1.0.0", "1.0.0", "print('one')\n"), ("v1.1.0", "1.1.0", "print('two')\n")],
     "clean", 0),
    ("drift",
     "Two releases. The code changed, and nobody bumped the version:\n"
     "    the label 1.0.0 now names two different programs.",
     [("v1.0.0", "1.0.0", "print('one')\n"), ("v1.0.1", "1.0.0", "print('two')\n")],
     "drift", 1),
    ("not enough to tell",
     "One release. There is nothing to compare its label with, and the tool says so\n"
     "    instead of saying 'clean'.",
     [("v1.0.0", "1.0.0", "print('one')\n")],
     "inconclusive", 2),
]


def git(repo, *args, day):
    when = "2020-01-%02dT12:00:00+00:00" % day
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, stdin=subprocess.DEVNULL,
                   env=dict(ENV, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when))


def main():
    if shutil.which("git") is None:
        print("git is not on PATH")
        return 2
    work = Path(tempfile.mkdtemp(prefix="closure-drift-demo-"))
    ok = True
    try:
        for n, (name, story, releases, want, want_code) in enumerate(CASES, start=1):
            repo = work / ("case%d" % n)
            (repo / "src").mkdir(parents=True)
            git(repo, "init", "-q", day=1)
            print("%d. %s\n    %s" % (n, name.upper(), story))
            for day, (tag, version, code) in enumerate(releases, start=1):
                (repo / "VERSION").write_text(version + "\n")
                (repo / "src" / "app.py").write_text(code)
                git(repo, "add", "-A", day=day)
                git(repo, "commit", "-q", "-m", tag, day=day)
                git(repo, "tag", tag, day=day)
                print("      tag %-7s VERSION says %s" % (tag, version))
            r = subprocess.run([sys.executable, str(DETECTOR), str(repo), "--json"],
                               capture_output=True, stdin=subprocess.DEVNULL, env=ENV)
            got = json.loads(r.stdout.decode("utf-8")).get("verdict")
            same = got == want and r.returncode == want_code
            ok = ok and same
            print("    closure_drift answers: %s (exit %d)   expected: %s (exit %d)   %s\n"
                  % (got, r.returncode, want, want_code, "as expected" if same else "DIFFERENT"))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("All three as expected." if ok else "Something differs from the expected answers.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
