#!/usr/bin/env python3
"""Write (or check) docs/DEMOS.md: three short sessions, each the real output of the detector.

    python3 tools/make_demos.py           # regenerate
    python3 tools/make_demos.py --check   # exit 1 if the committed page is stale

Every repository is built here with fixed dates and identities, so the page is the same bytes on
every machine and cannot drift from the program.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DETECTOR = ROOT / "closure_drift.py"
OUT = ROOT / "docs" / "DEMOS.md"
ENV = dict(os.environ, GIT_AUTHOR_NAME="demo", GIT_AUTHOR_EMAIL="demo@example.invalid",
           GIT_COMMITTER_NAME="demo", GIT_COMMITTER_EMAIL="demo@example.invalid",
           GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


class Repo:
    def __init__(self, work, name):
        self.path, self.day = work / name, 0
        (self.path / "src").mkdir(parents=True)
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")

    def git(self, *args):
        self.day += 1
        when = "2020-01-%02dT12:00:00+00:00" % self.day
        subprocess.run(["git", *args], cwd=self.path, check=True, capture_output=True, stdin=subprocess.DEVNULL,
                       env=dict(ENV, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when))

    def commit(self, message, version=None, tag=None, **files):
        if version is not None:
            (self.path / "VERSION").write_bytes((version + "\n").encode())
        for name, body in files.items():
            (self.path / "src" / (name.replace("_py", ".py"))).write_bytes(body.encode())
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        if tag:
            self.git("tag", tag)

    def run(self, *args, keep=None):
        """`closure-drift <args>` as a transcript: the command, then the lines worth reading."""
        r = subprocess.run([sys.executable, str(DETECTOR), *args], cwd=self.path, capture_output=True,
                           stdin=subprocess.DEVNULL, env=ENV)
        lines = (r.stdout + r.stderr).decode("utf-8").replace("\r\n", "\n").splitlines()
        cut = next((i for i, l in enumerate(lines) if l.startswith("Method:") or l.startswith("Between publication")),
                   len(lines))
        shown = [l for l in lines[:cut] if keep is None or any(k in l for k in keep)]
        while shown and not shown[-1].strip():
            shown.pop()
        return "$ %s\n%s\n(exit %d)" % (" ".join(("closure-drift",) + args), "\n".join(shown), r.returncode)


def build(work):
    a = Repo(work, "a")
    a.commit("release 1.0.0", version="1.0.0", tag="v1.0.0", app_py="print('one')\n")
    a.commit("fix a bug", app_py="print('two')\n")
    before = a.run("--would-tag")
    a.commit("bump the version", version="1.0.1")
    after = a.run("--would-tag")

    b = Repo(work, "b")
    b.commit("release 1.0.0", version="1.0.0", tag="v1.0.0", app_py="print('one')\n", util_py="x = 1\n")
    b.commit("release 1.0.1, version not bumped", tag="v1.0.1", app_py="print('two')\n", extra_py="y = 2\n")
    found = b.run()
    where = b.run("--compare", "v1.0.0", "v1.0.1")

    c = Repo(work, "c")
    c.commit("first release, no version file yet", tag="v0.1", app_py="print(0)\n")
    c.commit("second release, still none", tag="v0.2", app_py="print(1)\n")
    c.commit("release 1.0.0", version="1.0.0", tag="v1.0.0", app_py="print(2)\n")
    c.commit("release 1.1.0", version="1.1.0", tag="v1.1.0", app_py="print(3)\n")
    loose = c.run()
    strict = c.run("--strict")
    d = Repo(work, "d")
    d.commit("only release", version="1.0.0", tag="v1.0.0", app_py="print(0)\n")
    alone = d.run()

    return "\n".join([
        "# Three demonstrations",
        "",
        "Each block is the real output of `closure_drift` on a tiny repository built by",
        "`tools/make_demos.py`. CI rebuilds this page and fails if it differs.",
        "",
        "## A · Catch a version-label mistake before publishing",
        "",
        "`v1.0.0` is released. A fix is committed and the version file is not touched. Before tagging:",
        "",
        "```", before, "```",
        "",
        "After bumping the version:",
        "",
        "```", after, "```",
        "",
        "## B · Don't just flag drift. Show where it is.",
        "",
        "Two tags, `v1.0.0` and `v1.0.1`, and the version file still says `1.0.0` at both.",
        "",
        "```", found, "```",
        "",
        "```", where, "```",
        "",
        "## C · A check that cannot tell should say so",
        "",
        "Four tags; the first two were made before the project had a version file.",
        "",
        "```", loose, "```",
        "",
        "`clean`, over two of four tags — and the report says so. Asked to be strict, it does not pass:",
        "",
        "```", strict, "```",
        "",
        "And with one release there is nothing to compare its label with:",
        "",
        "```", alone, "```",
        "",
    ])


def main():
    work = Path(tempfile.mkdtemp(prefix="closure-drift-demos-"))
    try:
        page = build(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_bytes() != page.encode("utf-8"):
            print("docs/DEMOS.md differs from what the detector prints: run tools/make_demos.py and commit.")
            return 1
        print("docs/DEMOS.md is current")
        return 0
    OUT.write_bytes(page.encode("utf-8"))
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
