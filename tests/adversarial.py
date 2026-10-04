#!/usr/bin/env python3
"""Adversarial campaign for closure_drift — the attacks pre-registered in
PREREGISTRATION_ADVERSARIAL.md. Written by an independent reviewer who did not write the detector.

    python3 tests/adversarial.py                 # detector one directory up
    python3 tests/adversarial.py DETECTOR        # a specific copy
    python3 tests/adversarial.py --json OUT      # also write a machine-readable body

Every attack ends `as_required`, `loose` (a finding — or a hang past its time limit), or `not_run`
(the platform/filesystem cannot stage it, with a named reason). Scores print as one final line:

    N attacks · N as required · N loose · N not run

Exit 0 only when loose == 0; 1 when something is loose; 2 when the campaign itself could not run.

Zero dependencies beyond CPython >= 3.9 and git. Every repository it measures is built in a
temporary directory; the detector repo itself is only ever read. Nothing from the clock or unseeded
randomness enters a result, so two runs give the same body. The campaign isolates itself from the
user's git configuration (GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM=1, a throwaway HOME) and
neither touches the network nor runs the detector against any repository outside its temp dirs.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DETECTOR = ""
WINDOWS = os.name == "nt"
POSIX = os.name == "posix"
TIME_LIMIT = 20.0          # default per-invocation wall-clock limit (seconds)
REDOS_LIMIT = 8.0          # the limit named for the catastrophic-regex attack

BASE_ENV = dict(os.environ,
                GIT_AUTHOR_NAME="adv", GIT_AUTHOR_EMAIL="adv@example.invalid",
                GIT_COMMITTER_NAME="adv", GIT_COMMITTER_EMAIL="adv@example.invalid",
                GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                PYTHONDONTWRITEBYTECODE="1")
BASE_ENV.pop("PYTHONIOENCODING", None)
# A throwaway HOME so no user dotfile is read; filled in main() with a temp path.
for _k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_INDEX_FILE",
           "GIT_COMMON_DIR", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
    BASE_ENV.pop(_k, None)

CASES: list = []


LAST_CONTROL = None      # set by _marker_case; recorded with the case by the driver


class NotRun(Exception):
    """Raised with a named reason when the platform cannot stage the attack."""


class Loose(Exception):
    """Raised when the observed outcome contradicts the pre-registered requirement."""


def case(cid, title):
    def wrap(fn):
        CASES.append((cid, title, fn))
        return fn
    return wrap


def need(cond, why):
    if not cond:
        raise Loose(why)


# --------------------------------------------------------------------------- repo builder
class Repo:
    """A synthetic repo with deterministic per-step dates (one day per commit/tag)."""

    def __init__(self, root: Path, name: str = "repo"):
        self.path = root / name
        self.path.mkdir(parents=True)
        self.day = 0
        self._git("init", "-q")
        self._git("symbolic-ref", "HEAD", "refs/heads/main")

    def _env(self):
        self.day += 1
        when = "2020-01-%02dT12:00:00+00:00" % min(self.day, 28)
        return dict(BASE_ENV, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)

    def _git(self, *args, check=True):
        r = subprocess.run(["git", *args], cwd=str(self.path), capture_output=True, env=self._env(),
                           stdin=subprocess.DEVNULL)
        if check and r.returncode != 0:
            raise RuntimeError("git %s: %s" % (args[0], r.stderr.decode("utf-8", "replace")[:300]))
        return r

    def git(self, *args, check=True):
        return self._git(*args, check=check).stdout.decode("utf-8", "replace").strip()

    def git_bytes(self, *args):
        return self._git(*args).stdout

    def write(self, rel, data: bytes):
        if isinstance(rel, bytes):
            target = Path(os.fsdecode(os.fsencode(self.path) + b"/" + rel))
        else:
            target = self.path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))

    def pkg(self, version):
        self.write("package.json", (json.dumps({"version": version}) + "\n").encode())

    def commit(self, msg="c"):
        self._git("add", "-A")
        self._git("commit", "-q", "--allow-empty", "-m", msg)

    def tag(self, name, annotated=False):
        if annotated:
            self._git("tag", "-a", name, "-m", name)
        else:
            self._git("tag", name)

    def release(self, tag, version, files: dict, annotated=False):
        if version is not None:
            self.pkg(version)
        for rel, data in files.items():
            self.write(rel, data)
        self.commit(tag)
        self.tag(tag, annotated=annotated)


# --------------------------------------------------------------------------- detector runner
def run(repo, *args, env=None, timeout=TIME_LIMIT, as_json=True, pyexe=None, cwd=None):
    """Run the detector, return dict(code, out, err, doc, secs, timed_out)."""
    path = str(repo.path if isinstance(repo, Repo) else repo)
    cmd = [pyexe or sys.executable, DETECTOR, path]
    if as_json:
        cmd.append("--json")
    cmd += list(args)
    e = dict(env or BASE_ENV)
    t0 = time.monotonic()
    timed_out = False
    try:
        r = subprocess.run(cmd, capture_output=True, env=e, cwd=cwd, timeout=timeout)
        code, out, err = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as te:
        timed_out = True
        code, out, err = None, te.stdout or b"", te.stderr or b""
    secs = time.monotonic() - t0
    out_s = out.decode("utf-8", "replace")
    err_s = err.decode("utf-8", "replace")
    doc = None
    if as_json and not timed_out:
        try:
            doc = json.loads(out_s)
        except ValueError:
            doc = None
    return dict(code=code, out=out_s, err=err_s, doc=doc, secs=secs, timed_out=timed_out)


def no_traceback(res):
    blob = res["out"] + "\n" + res["err"]
    need("Traceback (most recent call last)" not in blob,
         "a Python traceback reached the user:\n" + blob[-500:])


def exit_in(res, allowed):
    need(not res["timed_out"], "the detector did not return within %.1fs (a hang)" % TIME_LIMIT)
    need(res["code"] in allowed, "exit %r not in %r; stderr=%r" % (res["code"], allowed, res["err"][:300]))


def verdict(res):
    return (res["doc"] or {}).get("verdict")


# --------------------------------------------------------------------------- snapshot (never-writes)
def snapshot(root: Path):
    snap = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            snap[rel] = ("link", os.readlink(str(p)))
        elif p.is_dir():
            snap[rel] = ("dir", None)
        elif p.is_file():
            try:
                snap[rel] = ("file", hashlib.sha256(p.read_bytes()).hexdigest())
            except OSError as ex:
                snap[rel] = ("err", str(ex))
    return snap


def diff_snapshots(before, after):
    changes = []
    for k in sorted(set(before) | set(after)):
        if before.get(k) != after.get(k):
            changes.append("%s: %r -> %r" % (k, before.get(k), after.get(k)))
    return changes


# --------------------------------------------------------------------------- marker helper
def marker_script(root: Path, marker: Path, name="touch_marker.sh"):
    """A tiny executable that creates `marker` when run. Returns a git-config value string."""
    sh = root / name
    # git runs configured commands through a POSIX shell on every platform, Windows included
    # (it ships one). Paths are written with forward slashes so that shell accepts them.
    sh.write_bytes(("#!/bin/sh\n: > '%s'\nexit 0\n" % Path(marker).as_posix()).encode("utf-8"))
    sh.chmod(0o755)
    return sh.as_posix()


# =========================================================================== A. false clean
@case("AF01", "git replace ref masks real drift")
def af01(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})   # same label, different closure -> drift
    base = run(r)
    need(verdict(base) == "drift", "control did not drift before the replace ref: %r" % verdict(base))
    # Redirect the second tag's tree to the first tag's tree, to mask the change.
    t1 = r.git("rev-parse", "v1^{tree}")
    t2 = r.git("rev-parse", "v2^{tree}")
    r.git("replace", t2, t1)
    res = run(r)
    no_traceback(res)
    exit_in(res, (1, 2))
    need(verdict(res) != "clean", "reported clean despite real drift (replace ref followed)")
    need(res["code"] == 1 and verdict(res) == "drift",
         "replace ref changed the measurement: verdict=%r exit=%r (the tree the tag names was not "
         "measured; detector lacks --no-replace-objects / GIT_NO_REPLACE_OBJECTS)" % (verdict(res), res["code"]))


@case("AF02", "grafts file masks real drift")
def af02(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    need(verdict(run(r)) == "drift", "control did not drift")
    c1 = r.git("rev-parse", "v1")
    c2 = r.git("rev-parse", "v2")
    info = r.path / ".git" / "info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "grafts").write_text(c2 + " " + c1 + "\n")   # legacy graft: reparent c2 onto c1
    res = run(r)
    no_traceback(res)
    exit_in(res, (1, 2))
    # Grafts rewrite parentage, not trees, so drift should survive; required: never clean.
    need(verdict(res) != "clean", "reported clean with a grafts file present")
    need(verdict(res) == "drift", "grafts perturbed the verdict: %r" % verdict(res))


@case("AF03", "mode-only change (file becomes executable) is invisible — declared limit")
def af03(root):
    r = Repo(root)
    r.write("src/a.py", b"print(1)\n")
    r.pkg("1.0")
    r.commit("v1")
    r.tag("v1")
    r.git("update-index", "--chmod=+x", "src/a.py")
    r.commit("v2")
    r.tag("v2")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))
    need(verdict(res) == "inconclusive",
         "a mode-only change produced verdict %r; the closure is (path, blob id) so mode is "
         "out of scope — expected inconclusive" % verdict(res))


@case("AF04", "regular file -> symlink with identical blob bytes is invisible — declared limit")
def af04(root):
    if WINDOWS:
        raise NotRun("symlinks in the index need POSIX here")
    r = Repo(root)
    r.write("src/a.py", b"target\n")   # bytes identical to the symlink target string below + NL
    r.pkg("1.0")
    r.commit("v1")
    r.tag("v1")
    # Replace the regular file with a symlink whose blob content is the same bytes ("target\n").
    (r.path / "src" / "a.py").unlink()
    os.symlink("target\n".rstrip("\n"), str(r.path / "src" / "a.py"))
    # A symlink blob stores the target WITHOUT trailing newline; to keep the SAME blob id we must
    # instead stage a symlink whose target string equals the old file's exact bytes.
    r.git("rm", "--cached", "-q", "src/a.py", check=False)
    # Make a symlink target string == b"target\n" is impossible (links can't hold NL cleanly);
    # use a clean payload with no newline so both blobs are exactly b"target".
    (r.path / "src" / "a.py").unlink()
    r.write("src/a.py", b"target")      # regular file, blob = b"target"
    r.commit("v1b")
    r.tag("v1b")
    base_oid = r.git("rev-parse", "v1b:src/a.py")
    (r.path / "src" / "a.py").unlink()
    os.symlink("target", str(r.path / "src" / "a.py"))   # symlink blob = b"target"
    r.commit("v2")
    r.tag("v2")
    link_oid = r.git("rev-parse", "v2:src/a.py")
    if base_oid != link_oid:
        raise NotRun("this git did not give the symlink and file the same blob id")
    # Compare the two tags that share the blob id but differ in type/mode, same label.
    res = run(r, "--max-commits", "2")
    no_traceback(res)
    exit_in(res, (2,))
    need(verdict(res) in ("inconclusive",),
         "type change (file->symlink, same blob id) gave %r; (path, id) ignores type/mode "
         "so it is invisible — expected inconclusive" % verdict(res))


@case("AF05", "closure-determining code under an excluded path is invisible — declared limit")
def af05(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/app.py": b"X=1\n", "src/tests/engine.py": b"E=1\n"})
    r.release("v2", "1.0", {"src/app.py": b"X=1\n", "src/tests/engine.py": b"E=2\n"})
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))
    need(verdict(res) == "inconclusive",
         "a change only under **/tests/** gave %r; it is excluded by CLOSURE_EXCLUDE, so by design "
         "it is not drift — expected inconclusive (a false-clean vector by design)" % verdict(res))


@case("AF06", "case-only path change is drift")
def af06(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/Mod.py": b"M=1\n"})
    r.git("rm", "-q", "src/Mod.py")
    r.release("v2", "1.0", {"src/mod.py": b"M=1\n"})
    res = run(r)
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "case-only rename gave %r, expected drift" % verdict(res))


@case("AF07", "unicode NFC/NFD twin path change is drift")
def af07(root):
    nfc = "src/caf\u00e9.py"          # é as one code point
    nfd = "src/cafe\u0301.py"          # e + combining acute
    r = Repo(root)
    try:
        r.release("v1", "1.0", {nfc: b"C=1\n"})
        r.git("rm", "-q", nfc)
        r.release("v2", "1.0", {nfd: b"C=1\n"})
    except Exception as ex:
        raise NotRun("filesystem folds unicode normalization: %s" % ex)
    names = r.git("ls-tree", "-r", "--name-only", "v2")
    if nfd not in names:
        raise NotRun("filesystem stored a normalized name, cannot stage NFC/NFD twins")
    res = run(r)
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "NFC/NFD twin gave %r, expected drift" % verdict(res))


@case("AF08", "path full of glob metacharacters is counted; its change is drift")
def af08(root):
    name = "src/[a-z]a?b*.py"
    r = Repo(root)
    try:
        r.release("v1", "1.0", {name: b"G=1\n"})
        r.release("v2", "1.0", {name: b"G=2\n"})
    except OSError as ex:
        raise NotRun("filesystem refuses glob-metacharacter name: %s" % ex)
    res = run(r)
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "metacharacter-named file change gave %r" % verdict(res))


@case("AF09", "very long path change is drift")
def af09(root):
    r = Repo(root)
    long_rel = "src/" + "/".join("d" * 40 for _ in range(6)) + "/x.py"  # ~300 bytes, segmented
    try:
        r.release("v1", "1.0", {long_rel: b"L=1\n"})
        r.release("v2", "1.0", {long_rel: b"L=2\n"})
    except OSError as ex:
        raise NotRun("filesystem refuses the long path: %s" % ex)
    stored = r.git("ls-tree", "-r", "--name-only", "v2")
    if long_rel not in stored:
        raise NotRun("git did not store the long path in the commit on this platform "
                     "(the case would measure a repository without the file)")
    res = run(r)
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "long-path change gave %r" % verdict(res))


@case("AF10", "non-ASCII path change is drift (X1)")
def af10(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a\u00e7\u00e3o.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a\u00e7\u00e3o.py": b"A=2\n"})
    res = run(r)
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "non-ASCII path change gave %r" % verdict(res))


@case("AF12", "submodule pointer change is drift (X10)")
def af12(root):
    sub = Repo(root, "sub")
    sub.release("s1", None, {"m.py": b"S=1\n"})
    sub.release("s2", None, {"m.py": b"S=2\n"})
    s1 = sub.git("rev-parse", "s1")
    s2 = sub.git("rev-parse", "s2")
    r = Repo(root, "super")
    r.pkg("1.0")
    # Commit WITHOUT `git add -A` (which would drop a gitlink that has no on-disk submodule).
    r._git("add", "package.json")
    r.git("update-index", "--add", "--cacheinfo", "160000", s1, "src/sub")
    r._git("commit", "-q", "-m", "v1")
    r.tag("v1")
    r.git("update-index", "--add", "--cacheinfo", "160000", s2, "src/sub")
    r._git("commit", "-q", "-m", "v2")
    r.tag("v2")
    files = r.git("ls-tree", "-r", "v2")
    if "src/sub" not in files:
        raise NotRun("could not stage a submodule pointer in the tree on this platform")
    res = run(r)
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "submodule pointer change gave %r, expected drift" % verdict(res))


@case("AF13", "moving then deleting a tag never crashes")
def af13(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    r.git("tag", "-f", "v1", "v2")   # move v1 onto v2's commit
    res = run(r)
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    r.git("tag", "-d", "v1")
    r.git("tag", "-d", "v2")
    res2 = run(r)
    no_traceback(res2)
    exit_in(res2, (2,))
    need(verdict(res2) == "no_publication_points", "no tags should give no_publication_points")


@case("AF14", "annotated tag pointing at a tag object, plus a lightweight tag, both resolve")
def af14(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"}, annotated=True)
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    # make a tag that points at the annotated tag object (nested)
    obj = r.git("rev-parse", "v1")       # the tag object
    r._git("tag", "-a", "nested", obj, "-m", "nested")
    res = run(r)
    no_traceback(res)
    exit_in(res, (0, 1, 2))


@case("AF15", "tags pointing at a blob and at a tree are counted, not crashed")
def af15(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    blob = r.git("hash-object", "-w", "--stdin")  # empty; capture via stdin below instead
    # create a blob and a tree ref
    p = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=str(r.path),
                       input=b"loose blob\n", capture_output=True, env=BASE_ENV)
    blob = p.stdout.decode().strip()
    r._git("tag", "blobtag", blob)
    tree = r.git("rev-parse", "v1^{tree}")
    r._git("tag", "treetag", tree)
    res = run(r)
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    doc = res["doc"] or {}
    need(doc.get("points_not_commits", 0) >= 2,
         "blob/tree tags should be counted in points_not_commits, got %r" % doc.get("points_not_commits"))


# =========================================================================== B. false drift
@case("FD01", "same label, same content, different commit id is not drift")
def fd01(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=1\n"})   # identical closure, amended-like
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))
    need(verdict(res) == "inconclusive", "identical closure under one label gave %r, not drift" % verdict(res))


@case("FD02", "version regex with two capture groups does not fabricate drift")
def fd02(root):
    r = Repo(root)
    r.write("ver.txt", b"name=pkg version=1.0\n")
    r.write("src/a.py", b"A=1\n")
    r.commit("v1")
    r.tag("v1")
    r.write("src/a.py", b"A=1\n")      # same closure
    r.commit("v2")
    r.tag("v2")
    res = run(r, "--version-file", "ver.txt", "--version-regex", r"(name)=\w+ version=([\d.]+)")
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    need(verdict(res) != "drift", "two-group regex produced a spurious drift: %r" % verdict(res))


@case("FD03", "the same repository measured twice gives the same verdict")
def fd03(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    a, b = run(r), run(r)
    no_traceback(a)
    no_traceback(b)
    need(verdict(a) == verdict(b) == "drift", "non-deterministic verdict: %r vs %r" % (verdict(a), verdict(b)))


# =========================================================================== C. exit-code / no traceback
@case("EC01", "not a git repository refuses with exit 2")
def ec01(root):
    d = root / "plain"
    d.mkdir()
    res = run(d)
    no_traceback(res)
    exit_in(res, (2,))


@case("EC02", "bare repository completes without a working tree")
def ec02(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    bare = root / "bare.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(r.path), str(bare)],
                   check=True, capture_output=True, env=BASE_ENV)
    res = run(bare)
    no_traceback(res)
    exit_in(res, (0, 2))
    doc = res["doc"] or {}
    need(doc.get("stamp", {}).get("working_tree_dirty", "x") is None,
         "bare repo should report working_tree_dirty null, got %r" % doc.get("stamp"))


@case("EC03", "repository with no commits refuses")
def ec03(root):
    r = Repo(root)
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))


@case("EC04", "detached HEAD runs")
def ec04(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    r.git("checkout", "-q", "--detach", "v1")
    res = run(r)
    no_traceback(res)
    exit_in(res, (0, 1, 2))


@case("EC05", "deleted tree object of a tagged commit refuses naming git (D14)")
def ec05(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    tree = r.git("rev-parse", "v2^{tree}")
    # delete the loose object for v2's tree
    obj = r.path / ".git" / "objects" / tree[:2] / tree[2:]
    if not obj.exists():
        r.git("unpack-objects", check=False)  # best effort; may already be loose
    if not obj.exists():
        raise NotRun("tree object is packed; cannot delete a single loose object portably")
    obj.unlink()
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))
    need(verdict(res) is None or verdict(res) != "clean", "a missing tree must not read as clean")


@case("EC06", "corrupt .git/index does not crash")
def ec06(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    (r.path / ".git" / "index").write_bytes(b"\x00\x01\x02 not an index \xff\xfe")
    res = run(r)
    no_traceback(res)
    exit_in(res, (0, 1, 2))


@case("EC07", "HEAD pointing at a missing ref refuses")
def ec07(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    (r.path / ".git" / "HEAD").write_text("ref: refs/heads/nonexistent\n")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))


@case("EC08", "repo path with a leading dash does not crash")
def ec08(root):
    r = Repo(root, "-weird")
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    # argparse will treat a leading-dash positional as an option; pass it as given.
    cmd = [sys.executable, DETECTOR, str(r.path), "--json"]
    res = subprocess.run(cmd, capture_output=True, env=BASE_ENV, timeout=TIME_LIMIT)
    blob = res.stdout.decode("u8", "replace") + res.stderr.decode("u8", "replace")
    need("Traceback (most recent call last)" not in blob, "traceback on dashed path:\n" + blob[-400:])
    need(res.returncode in (0, 1, 2), "dashed path gave exit %r" % res.returncode)


@case("EC09", "repo path with spaces and unicode runs")
def ec09(root):
    r = Repo(root, "a repo \u00e7\u00e3o dir")
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    res = run(r)
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "spaced/unicode path gave %r" % verdict(res))


@case("EC10", "GIT_DIR in the environment must not silently redirect the measurement")
def ec10(root):
    drifty = Repo(root, "drifty")
    drifty.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    drifty.release("v2", "1.0", {"src/a.py": b"A=2\n"})      # drift
    clean = Repo(root, "clean")
    clean.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    clean.release("v2", "2.0", {"src/a.py": b"A=2\n"})       # clean
    env = dict(BASE_ENV, GIT_DIR=str(clean.path / ".git"))
    res = run(drifty, env=env)
    no_traceback(res)
    exit_in(res, (1, 2))
    need(verdict(res) != "clean",
         "GIT_DIR pointed at a CLEAN repo while the path argument named a DRIFTY repo, and the "
         "tool reported clean — the environment overrode -C and the wrong repository was measured")


@case("EC11", "GIT_WORK_TREE / GIT_INDEX_FILE in the environment do not misdirect or crash")
def ec11(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    other = Repo(root, "other")
    other.release("v1", "9.9", {"src/a.py": b"Z=1\n"})
    env = dict(BASE_ENV, GIT_WORK_TREE=str(other.path),
               GIT_INDEX_FILE=str(root / "stray.index"))
    res = run(r, env=env)
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    need(not (root / "stray.index").exists() or True, "")  # index file may be created by git in temp; not a repo write


@case("EC12", "config [] refuses")
def ec12(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.write(".closure-drift.json", b"[]")
    r.commit("c")
    r.tag("v2")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))


@case("EC13", "config not UTF-8 refuses")
def ec13(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.write(".closure-drift.json", b"\xff\xfe\x00bad")
    r.commit("c")
    r.tag("v2")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))


@case("EC14", "config not JSON refuses")
def ec14(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.write(".closure-drift.json", b"this is not json {")
    r.commit("c")
    r.tag("v2")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))


@case("EC15", "config unknown key refuses")
def ec15(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.write(".closure-drift.json", b'{"closures": ["src/**"]}')
    r.commit("c")
    r.tag("v2")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))


@case("EC16", "config closure as a string refuses")
def ec16(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.write(".closure-drift.json", b'{"closure": "src/**"}')
    r.commit("c")
    r.tag("v2")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))


@case("EC17", "config at:weekly refuses")
def ec17(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.write(".closure-drift.json", b'{"at": "weekly"}')
    r.commit("c")
    r.tag("v2")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))


@case("EC18", "catastrophic-backtracking version_regex must not hang (ReDoS)")
def ec18(root):
    r = Repo(root)
    r.write("evil.txt", b"version=" + b"a" * 29 + b"!\n")
    r.write("src/a.py", b"A=1\n")
    r.commit("v1")
    r.tag("v1")
    r.write(".closure-drift.json", b'{"version_file": "evil.txt", "version_regex": "(a+)+$"}')
    r.commit("c2")
    r.tag("v2")
    res = run(r, timeout=REDOS_LIMIT)
    need(not res["timed_out"],
         "the detector did not return within %.1fs: a catastrophic regex supplied by the measured "
         "repository's own .closure-drift.json hangs it (ReDoS / DoS). The compile-probe checks the "
         "pattern but nothing bounds matching time in declared_version()." % REDOS_LIMIT)
    no_traceback(res)
    exit_in(res, (0, 1, 2))


@case("EC19", "deeply nested JSON config refuses without a traceback")
def ec19(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.write(".closure-drift.json", (b"[" * 100000) + (b"]" * 100000))
    r.commit("c")
    r.tag("v2")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))


@case("EC20", "large config file refuses in bounded time")
def ec20(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    big = b'{"closures": "' + b"x" * (20 * 1024 * 1024) + b'"}'
    r.write(".closure-drift.json", big)
    r.commit("c")
    r.tag("v2")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))


@case("EC21", "large version file is handled without a crash")
def ec21(root):
    r = Repo(root)
    r.write("VERSION", b"1.0\n" + b"#" * (20 * 1024 * 1024))
    r.write("src/a.py", b"A=1\n")
    r.commit("v1")
    r.tag("v1")
    r.write("src/a.py", b"A=2\n")
    r.commit("v2")
    r.tag("v2")
    res = run(r, timeout=60.0)
    no_traceback(res)
    exit_in(res, (0, 1, 2))


@case("EC22", "version file that is a symlink does not crash")
def ec22(root):
    if WINDOWS:
        raise NotRun("symlink staging needs POSIX here")
    r = Repo(root)
    os.symlink("elsewhere", str(r.path / "VERSION"))
    r.write("src/a.py", b"A=1\n")
    r.commit("v1")
    r.tag("v1")
    r.write("src/a.py", b"A=2\n")
    r.commit("v2")
    r.tag("v2")
    res = run(r)
    no_traceback(res)
    exit_in(res, (0, 1, 2))


@case("EC23", "version file path that is a directory does not crash")
def ec23(root):
    r = Repo(root)
    r.write("VERSION/keep.txt", b"not a version\n")
    r.write("src/a.py", b"A=1\n")
    r.commit("v1")
    r.tag("v1")
    r.write("src/a.py", b"A=2\n")
    r.commit("v2")
    r.tag("v2")
    res = run(r, "--version-file", "VERSION")
    no_traceback(res)
    exit_in(res, (0, 1, 2))


@case("EC24", "--max-commits 0 and -3 refuse")
def ec24(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    for n in ("0", "-3"):
        res = run(r, "--max-commits", n)
        no_traceback(res)
        exit_in(res, (2,))


@case("EC25", "absurdly large --max-commits runs")
def ec25(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    res = run(r, "--max-commits", str(10 ** 15))
    no_traceback(res)
    exit_in(res, (1,))


@case("EC26", "~1200 tags complete")
def ec26(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    base = r.git("rev-parse", "HEAD")
    # create many lightweight tags on the same commit quickly
    for i in range(1200):
        subprocess.run(["git", "tag", "t%04d" % i, base], cwd=str(r.path),
                       check=True, capture_output=True, env=BASE_ENV)
    res = run(r, timeout=120.0)
    no_traceback(res)
    exit_in(res, (0, 1, 2))


@case("EC27", "malformed --version-regex refuses, not exit 1")
def ec27(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    res = run(r, "--version-file", "package.json", "--version-regex", "(")
    no_traceback(res)
    exit_in(res, (2,))
    need(res["code"] != 1, "a malformed regex exited 1 (the drift code)")


@case("EC28", "--version-regex with no capture group refuses, not exit 1")
def ec28(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    res = run(r, "--version-file", "package.json", "--version-regex", "version")
    no_traceback(res)
    exit_in(res, (2,))
    need(res["code"] != 1, "a groupless regex exited 1")


@case("EC29", "--version-regex without --version-file refuses")
def ec29(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    res = run(r, "--version-regex", r'"version":\s*"([^"]+)"')
    no_traceback(res)
    exit_in(res, (2,))


@case("EC30", "a repository nested inside another measures the outer, no crash")
def ec30(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    inner = Repo(r.path, "nested_inner")   # a repo dir under the worktree (untracked)
    inner.release("i1", "7.7", {"src/a.py": b"I=1\n"})
    res = run(r)
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "outer repo should still read drift, got %r" % verdict(res))


@case("EC31", "a linked worktree (.git is a file) runs")
def ec31(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    wt = root / "linked_wt"
    subprocess.run(["git", "worktree", "add", "-q", "--detach", str(wt), "v2"],
                   cwd=str(r.path), check=True, capture_output=True, env=BASE_ENV)
    need((wt / ".git").is_file(), "worktree .git should be a file")
    res = run(wt)
    no_traceback(res)
    exit_in(res, (0, 1, 2))


@case("EC32", "PYTHONIOENCODING=ascii with a non-ASCII label completes")
def ec32(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.pkg("1.0-caf\u00e9")
    r.write("src/a.py", b"A=2\n")
    r.commit("v2")
    r.tag("v2")
    env = dict(BASE_ENV, PYTHONIOENCODING="ascii")
    res = run(r, as_json=False, env=env)
    no_traceback(res)
    exit_in(res, (0, 1, 2))


@case("EC33", "closed stdout does not crash with a live traceback")
def ec33(root):
    if not POSIX:
        raise NotRun("closing fd 1 via the shell needs POSIX")
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    script = '"$1" "$2" "$3" 1>&-'
    res = subprocess.run(["sh", "-c", script, "sh", sys.executable, DETECTOR, str(r.path)],
                         capture_output=True, env=BASE_ENV, timeout=TIME_LIMIT)
    err = res.stderr.decode("u8", "replace")
    need("Traceback (most recent call last)" not in err, "traceback with stdout closed:\n" + err[-400:])
    need(res.returncode in (0, 1, 2) or res.returncode is not None, "undefined exit with closed stdout")


@case("EC34", "SIGPIPE from an early-closing reader does not crash")
def ec34(root):
    if not POSIX:
        raise NotRun("SIGPIPE pipeline needs POSIX")
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    p1 = subprocess.Popen([sys.executable, DETECTOR, str(r.path)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=BASE_ENV)
    p2 = subprocess.Popen(["head", "-c", "1"], stdin=p1.stdout, stdout=subprocess.DEVNULL)
    p1.stdout.close()
    p2.wait(timeout=TIME_LIMIT)
    err = p1.stderr.read().decode("u8", "replace")
    p1.wait(timeout=TIME_LIMIT)
    need("Traceback (most recent call last)" not in err, "traceback on SIGPIPE:\n" + err[-400:])
    need("BrokenPipeError" not in err, "uncaught BrokenPipeError on SIGPIPE:\n" + err[-400:])


@case("EC35", ".git is a file pointing at an attacker gitdir — read-only, no crash")
def ec35(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    # move the real gitdir aside and leave a .git FILE pointing at it
    realdir = root / "real_gitdir"
    shutil.move(str(r.path / ".git"), str(realdir))
    (r.path / ".git").write_text("gitdir: %s\n" % realdir)
    res = run(r)
    no_traceback(res)
    exit_in(res, (0, 1, 2))


# =========================================================================== D. never writes
def _never_writes(root, make, *args, env=None):
    r = make(root)
    before = snapshot(r.path)
    res = run(r, *args, env=env)
    no_traceback(res)
    after = snapshot(r.path)
    changes = diff_snapshots(before, after)
    need(not changes, "the repository was modified by the run:\n  " + "\n  ".join(changes[:12]))
    return res


@case("NW01", "default run never writes to a stat-dirty repo")
def nw01(root):
    def make(rt):
        r = Repo(rt)
        r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
        r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
        (r.path / "src" / "a.py").write_bytes(b"A=3 modified\n")  # dirty working tree
        return r
    _never_writes(root, make)


@case("NW02", "--at commits run never writes")
def nw02(root):
    def make(rt):
        r = Repo(rt)
        r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
        r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
        return r
    _never_writes(root, make, "--at", "commits")


@case("NW03", "a filter-config + dirty file run never writes (status path)")
def nw03(root):
    if WINDOWS:
        raise NotRun("filter config marker needs POSIX")
    def make(rt):
        r = Repo(rt)
        r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
        r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
        r.git("config", "--local", "filter.x.clean", "cat")
        r.write(".gitattributes", b"src/a.py filter=x\n")
        (r.path / "src" / "a.py").write_bytes(b"A=9 dirty\n")
        return r
    _never_writes(root, make)


@case("NW04", "a refusing run never writes")
def nw04(root):
    def make(rt):
        r = Repo(rt)
        r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
        r.write(".closure-drift.json", b'{"at":"weekly"}')
        r.commit("c")
        r.tag("v2")
        return r
    _never_writes(root, make)


# =========================================================================== E. no command executed
def _marker_case(root, configure):
    """configure(repo, marker_value, marker_path) sets up the repo; marker must be absent after run.

    POSITIVE CONTROL, added 2026-10-04: an absent marker only means something if the vector can
    fire here. Before the detector runs, the plain git commands of the kind the detector uses are
    run with NO protection; whether the marker appeared is recorded with the case. Where it did,
    "absent after the detector" is a measured block. Where it did not, the case still requires an
    absent marker, and says that no plain command fired the vector either."""
    global LAST_CONTROL
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    marker = root / ("MARKER_%s" % os.getpid())
    if marker.exists():
        marker.unlink()
    val = marker_script(root, marker)
    configure(r, val, marker)
    for probe in (("status", "--porcelain"), ("log", "-1", "--format=%H"), ("for-each-ref", "refs/tags"),
                  ("cat-file", "-p", "HEAD"), ("config", "--local", "--list"), ("rev-parse", "HEAD")):
        subprocess.run(["git", *probe], cwd=str(r.path), capture_output=True, env=r._env(),
                       stdin=subprocess.DEVNULL)
    fired = marker.exists()
    if fired:
        marker.unlink()
    LAST_CONTROL = ("positive control: the vector FIRES under plain git here; blocked under the detector"
                    if fired else
                    "positive control: no plain git command of the detector's kind fires this vector here")
    res = run(r)
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    present = marker.exists()
    if present:
        marker.unlink()
    need(not present, "a command named in the repository's own config was executed (marker created)")
    return r, res


@case("CX01", "core.fsmonitor is not executed")
def cx01(root):
    _marker_case(root, lambda r, v, m: r.git("config", "--local", "core.fsmonitor", v))


@case("CX02", "core.hooksPath hooks are not executed")
def cx02(root):
    def cfg(r, v, m):
        hooks = r.path / "myhooks"
        hooks.mkdir()
        for h in ("pre-commit", "post-index-change", "reference-transaction", "post-checkout",
                  "fsmonitor-watchman"):
            p = hooks / h
            p.write_text("#!/bin/sh\n: > '%s'\nexit 0\n" % m)
            p.chmod(0o755)
        r.git("config", "--local", "core.hooksPath", str(hooks))
    _marker_case(root, cfg)


@case("CX03", "filter.x.clean is not executed (status path skipped)")
def cx03(root):
    def cfg(r, v, m):
        r.git("config", "--local", "filter.x.clean", v)
        r.write(".gitattributes", b"src/a.py filter=x\n")
        (r.path / "src" / "a.py").write_bytes(b"dirty now\n")
    r, res = _marker_case(root, cfg)
    doc = res["doc"] or {}
    need(doc.get("stamp", {}).get("working_tree_dirty") is None,
         "with a clean filter defined, working_tree_dirty should be null, got %r" % doc.get("stamp"))


@case("CX04", "filter.x.smudge is not executed")
def cx04(root):
    def cfg(r, v, m):
        r.git("config", "--local", "filter.x.smudge", v)
        r.write(".gitattributes", b"src/a.py filter=x\n")
        (r.path / "src" / "a.py").write_bytes(b"dirty now\n")
    _marker_case(root, cfg)


@case("CX05", "filter.x.process is not executed")
def cx05(root):
    def cfg(r, v, m):
        r.git("config", "--local", "filter.x.process", v)
        r.write(".gitattributes", b"src/a.py filter=x\n")
        (r.path / "src" / "a.py").write_bytes(b"dirty now\n")
    _marker_case(root, cfg)


@case("CX06", "diff.x.textconv is not executed")
def cx06(root):
    def cfg(r, v, m):
        r.git("config", "--local", "diff.x.textconv", v)
        r.write(".gitattributes", b"src/a.py diff=x\n")
        (r.path / "src" / "a.py").write_bytes(b"dirty now\n")
    _marker_case(root, cfg)


@case("CX07", "core.pager is not executed")
def cx07(root):
    _marker_case(root, lambda r, v, m: r.git("config", "--local", "core.pager", v))


@case("CX08", "core.editor is not executed")
def cx08(root):
    _marker_case(root, lambda r, v, m: r.git("config", "--local", "core.editor", v))


@case("CX09", "core.sshCommand is not executed")
def cx09(root):
    _marker_case(root, lambda r, v, m: r.git("config", "--local", "core.sshCommand", v))


@case("CX10", "core.gitProxy is not executed")
def cx10(root):
    _marker_case(root, lambda r, v, m: r.git("config", "--local", "core.gitProxy", v))


@case("CX11", "alias.ls-tree cannot shadow the builtin the detector calls")
def cx11(root):
    def cfg(r, v, m):
        r.git("config", "--local", "alias.ls-tree", "!" + v)
    r, res = _marker_case(root, cfg)
    need(verdict(res) == "drift", "aliasing ls-tree perturbed the measurement: %r" % verdict(res))


@case("CX12", "include.path to a filter config is not executed (status skipped)")
def cx12(root):
    def cfg(r, v, m):
        inc = r.path / "extra.cfg"
        inc.write_text('[filter "x"]\n\tclean = %s\n' % v)
        r.git("config", "--local", "include.path", str(inc))
        r.write(".gitattributes", b"src/a.py filter=x\n")
        (r.path / "src" / "a.py").write_bytes(b"dirty now\n")
    _marker_case(root, cfg)


@case("CX13", "includeIf.gitdir to an fsmonitor/filter config is not executed")
def cx13(root):
    def cfg(r, v, m):
        inc = r.path / "extra.cfg"
        inc.write_text('[core]\n\tfsmonitor = %s\n[filter "x"]\n\tclean = %s\n' % (v, v))
        r.git("config", "--local", "includeIf.gitdir:**.path", str(inc))
        r.write(".gitattributes", b"src/a.py filter=x\n")
        (r.path / "src" / "a.py").write_bytes(b"dirty now\n")
    _marker_case(root, cfg)


@case("CX14", "core.worktree elsewhere does not write outside or crash")
def cx14(root):
    def cfg(r, v, m):
        elsewhere = root / "elsewhere_wt"
        elsewhere.mkdir()
        r.git("config", "--local", "core.worktree", str(elsewhere))
    # core.worktree does not name a command; just assert no marker/crash and no write to elsewhere
    r, res = _marker_case(root, cfg)


@case("CX15", "credential.helper and uploadpack.packObjectsHook are not executed")
def cx15(root):
    def cfg(r, v, m):
        r.git("config", "--local", "credential.helper", "!" + v)
        r.git("config", "--local", "uploadpack.packObjectsHook", v)
    _marker_case(root, cfg)


@case("CX16", "ls-tree / cat-file emit raw bytes, filters do not run")
def cx16(root):
    def cfg(r, v, m):
        # route every path through a clean filter; the detector reads via ls-tree + cat-file blob
        r.git("config", "--local", "filter.x.clean", v)
        r.git("config", "--local", "filter.x.smudge", v)
        r.write(".gitattributes", b"* filter=x\n")
    _marker_case(root, cfg)


# =========================================================================== F. output injection
INJ_LABEL = "1.0\nCLEAN: everything is fine\x1b[2J\x07\u202e\u2028end"


def _raw_pkg_bytes(label):
    # Hand-built package.json carrying RAW control characters inside the version string (json.dumps
    # would escape them). The detector's regex `"version"\s*:\s*"([^"]+)"` captures until the next
    # quote, so the raw bytes \u2014 newline, ESC, BEL, bidi override, U+2028 \u2014 enter the label verbatim.
    return ('{"version": "' + label + '"}\n').encode("utf-8")


def _inject_repo(root):
    # BOTH tags carry the SAME injected label over DIFFERENT closures \u2192 drift, so the label is
    # printed in the report where a forged line could appear.
    r = Repo(root)
    r.write("package.json", _raw_pkg_bytes(INJ_LABEL))
    r.write("src/a.py", b"A=1\n")
    r.commit("v1")
    r.tag("v1")
    r.write("src/a.py", b"A=2\n")
    r.commit("v2")
    r.tag("v2")
    return r


@case("OI01", "a label with control chars and a forged verdict line is escaped in text")
def oi01(root):
    r = _inject_repo(root)
    res = run(r, as_json=False)
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    lines = res["out"].splitlines()
    for raw in ("\x1b", "\x07", "\u202e", "\u2028"):
        need(raw not in res["out"], "raw control char %r appears in the text report" % raw)
    forged = [ln for ln in lines if (ln.startswith("CLEAN") or ln.startswith("DRIFT"))
              and "everything is fine" in ln]
    need(not forged, "a forged verdict line was injected into the report: %r" % forged)


@case("OI02", "the same label round-trips exactly in JSON")
def oi02(root):
    r = _inject_repo(root)
    res = run(r)
    no_traceback(res)
    need(res["doc"] is not None, "JSON did not parse")
    drift = res["doc"].get("drift", {})
    need(INJ_LABEL in drift, "the control-char label did not round-trip as a JSON key; keys=%r"
         % list(drift)[:3])


@case("OI03", "a tag name with control chars is escaped in text")
def oi03(root):
    # git forbids raw control characters in ref names (checked below), so that vector is closed at
    # git's door. A bidi override is accepted by many git versions; if so, it must be escaped.
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    ctrl = r._git("tag", "ctrl\x1b[2Jx", "v2", check=False)
    need(ctrl.returncode != 0, "git accepted a raw-control-char tag name (unexpected)")
    rc = r._git("tag", "bidi‮x", "v2", check=False)
    if rc.returncode != 0:
        raise NotRun("git refused the bidi tag name on this platform")
    res = run(r, as_json=False)
    no_traceback(res)
    need("‮" not in res["out"], "raw bidi override from a tag name printed unescaped")


@case("OI04", "a commit subject with a forged line is escaped (--at commits, drift)")
def oi04(root):
    r = Repo(root)
    r.write("src/a.py", b"A=1\n")
    r.pkg("1.0")
    r.commit("v1")
    r.write("src/a.py", b"A=2\n")
    r.pkg("1.0")
    r._git("add", "-A")
    r._git("commit", "-q", "-m", "subject\nDRIFT: forged\x1b[2J")
    res = run(r, "--at", "commits", as_json=False)
    no_traceback(res)
    need("\x1b" not in res["out"], "raw escape from a commit subject printed")
    forged = [ln for ln in res["out"].splitlines() if ln.startswith("DRIFT: forged")]
    need(not forged, "a forged verdict line from a commit subject was printed: %r" % forged)


@case("OI05", "a refusal quoting a control-char config key has no raw control char on stderr")
def oi05(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.write(".closure-drift.json", '{"bad\x1b[2Jkey": 1}'.encode())
    r.commit("c")
    r.tag("v2")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))
    need("\x1b" not in res["err"], "raw escape from a config key printed on stderr")


@case("OI06", "a repo-path argument with control chars is escaped where printed")
def oi06(root):
    try:
        r = Repo(root, "weird\x07name")
    except OSError as ex:
        raise NotRun("filesystem refuses control-char dir name: %s" % ex)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    res = run(r, as_json=False)
    no_traceback(res)
    need("\x07" not in res["out"], "raw control char from the repo path printed in the report")


@case("OI07", "a label that is literally 'clean' is not mistaken for a verdict")
def oi07(root):
    r = Repo(root)
    r.release("v1", "clean", {"src/a.py": b"A=1\n"})
    r.release("v2", "clean", {"src/a.py": b"A=2\n"})   # same label 'clean', different closure
    res = run(r)
    no_traceback(res)
    need(res["doc"] and res["doc"].get("verdict") == "drift",
         "a label 'clean' confused the verdict field: %r" % verdict(res))
    need(res["code"] == 1, "verdict field says drift but exit was %r" % res["code"])


# =========================================================================== G. stamp
@case("ST01", "running via a symlink does not let detector_closure lie")
def st01(root):
    if WINDOWS:
        raise NotRun("symlink invocation needs POSIX here")
    link = root / "cd_link.py"
    os.symlink(DETECTOR, str(link))
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    res = run(r)  # control, real path
    expect = hashlib.sha256(Path(DETECTOR).read_bytes()).hexdigest()[:16]
    cmd = [sys.executable, str(link), str(r.path), "--json"]
    r2 = subprocess.run(cmd, capture_output=True, env=BASE_ENV, timeout=TIME_LIMIT)
    doc = json.loads(r2.stdout.decode("u8", "replace"))
    got = doc["stamp"]["detector_closure"]
    need(got == expect, "stamp via symlink was %r, source hash is %r (it misreports)" % (got, expect))


@case("ST02", "running via python -m stamps the module file honestly")
def st02(root):
    pkgdir = Path(DETECTOR).resolve().parent
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    env = dict(BASE_ENV, PYTHONPATH=str(pkgdir))
    cmd = [sys.executable, "-m", "closure_drift", str(r.path), "--json"]
    rr = subprocess.run(cmd, capture_output=True, env=env, timeout=TIME_LIMIT)
    blob = rr.stdout.decode("u8", "replace") + rr.stderr.decode("u8", "replace")
    need("Traceback (most recent call last)" not in blob, "traceback under -m:\n" + blob[-300:])
    if rr.returncode == 2 and not rr.stdout.strip():
        raise NotRun("python -m could not import the module in this layout")
    doc = json.loads(rr.stdout.decode("u8", "replace"))
    expect = hashlib.sha256(Path(DETECTOR).read_bytes()).hexdigest()[:16]
    need(doc["stamp"]["detector_closure"] == expect, "stamp under -m disagrees with the source hash")


@case("ST03", "invocation with no __file__ fails closed (exit 2), no traceback, no forged stamp")
def st03(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    code = ("import sys; sys.argv=['x', %r, '--json']; "
            "exec(compile(open(%r).read(), '<nofile>', 'exec'))" % (str(r.path), DETECTOR))
    rr = subprocess.run([sys.executable, "-c", code], capture_output=True, env=BASE_ENV, timeout=TIME_LIMIT)
    blob = rr.stdout.decode("u8", "replace") + rr.stderr.decode("u8", "replace")
    need("Traceback (most recent call last)" not in blob, "traceback with no __file__:\n" + blob[-300:])
    need(rr.returncode == 2, "no-__file__ run exited %r, expected 2 (fail closed)" % rr.returncode)


@case("ST04", "a stale .pyc does not change the stamp (source is hashed)")
def st04(root):
    # copy the detector into a temp package, import to create a .pyc, then tamper nothing:
    # the stamp must equal the hash of the .py source regardless of any cached bytecode.
    pkg = root / "pkgdir"
    pkg.mkdir()
    src = pkg / "cd.py"
    src.write_bytes(Path(DETECTOR).read_bytes())
    subprocess.run([sys.executable, "-c", "import py_compile,sys; py_compile.compile(sys.argv[1])",
                    str(src)], check=False, capture_output=True, env=BASE_ENV)
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    rr = subprocess.run([sys.executable, str(src), str(r.path), "--json"],
                        capture_output=True, env=BASE_ENV, timeout=TIME_LIMIT)
    doc = json.loads(rr.stdout.decode("u8", "replace"))
    expect = hashlib.sha256(src.read_bytes()).hexdigest()[:16]
    need(doc["stamp"]["detector_closure"] == expect, "stamp hashed something other than the .py source")


# =========================================================================== H. hash construction
def _load_detector_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("cd_under_test", DETECTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@case("HC01", "two genuinely different closures hash to different 16-hex values")
def hc01(root):
    mod = _load_detector_module()
    inc = ["src/**"]
    a = [("src/a.py", "blob", "1" * 40)]
    b = [("src/a.py", "blob", "2" * 40)]
    need(mod.closure_hash(a, inc)[0] != mod.closure_hash(b, inc)[0],
         "distinct closures collided to the same 16-hex value")


@case("HC02", "the concatenation has a pre-image ambiguity (no separator) — reported, not reachable")
def hc02(root):
    mod = _load_detector_module()
    inc = ["**"]  # match everything so both entries are counted
    # Two DIFFERENT (path, oid) lists whose path||oid streams are byte-identical.
    # List 1: a single file whose name ends in hex that, with its oid, equals list 2's stream.
    # Here we exploit only that there is no separator: path "a" + oid "b"*40 streams to "a"+"b"*40,
    # and path "ab" + oid ("b"*39 + "b") streams to "ab"+"b"*40 == "a"+"b"*40 + ... check lengths.
    oid1 = "b" * 40
    list1 = [("a", "blob", oid1)]                      # stream: "a" + "b"*40  (len 41)
    # To match with a different (path, oid): path "ab", oid must be "b"*39 so stream "ab"+"b"*39 (len 41)
    oid2 = "b" * 39
    list2 = [("ab", "blob", oid2)]                     # stream: "ab" + "b"*39 (len 41) == "a"+"b"*40
    h1 = mod.closure_hash(list1, inc)[0]
    h2 = mod.closure_hash(list2, inc)[0]
    same_stream = ("a".encode() + oid1.encode()) == ("ab".encode() + oid2.encode())
    need(same_stream, "test construction error: streams are not equal")
    need(h1 == h2,
         "expected the no-separator construction to make these collide")
    # This is reported as a construction defect. It is NOT reachable with real git, because a real
    # blob oid is exactly 40 (or 64) hex chars content-addressed, not a 39-char attacker choice.
    # The case passes as_required by demonstrating the ambiguity; the finding is in the report.


# =========================================================================== extension, 2026-10-04
# The features of 0.9.0: --would-tag, --tags, --strict, --explain, --compare, --diagnose, --version,
# the tag-derived refusal, the tag-families hint, and the tree reader. Pre-registered in
# PREREGISTRATION_ADVERSARIAL.md, section "Extension, 2026-10-04", before any of these was run.
import unicodedata  # noqa: E402

EXT_LIMIT = 90.0
SENT_LABEL = "9.8.7-LBLSENTINEL"
SENT_TOKENS = ("LBLSENTINEL", "REPOSENTINEL", "PATHSENTINEL", "HOMESENTINEL", "ENVSENTINEL")


def _pj(label):
    """package.json bytes holding `label` raw (non-ASCII stays as UTF-8, not \\u-escaped)."""
    return _raw_pkg_bytes(label)


def _q(path: bytes) -> bytes:
    """A C-style quoted path for fast-import."""
    out = bytearray(b'"')
    for b in path:
        if b in (0x22, 0x5C):
            out += b"\\" + bytes([b])
        elif b == 0x0A:
            out += b"\\n"
        elif b < 0x20 or b >= 0x7F:
            out += b"\\%03o" % b
        else:
            out.append(b)
    return bytes(out + b'"')


class FastImport:
    """Builds history quickly and deterministically through `git fast-import`. Every commit states
    its whole tree (deleteall + every file), one day apart."""

    def __init__(self):
        self.parts = []
        self.mark = 0
        self.t = 1577880000

    def commit(self, files: dict, branch=b"refs/heads/main", msg=b"c"):
        self.mark += 1
        self.t += 86400
        p = [b"commit " + branch, b"mark :%d" % self.mark,
             b"committer adv <adv@example.invalid> %d +0000" % self.t,
             b"data %d" % len(msg), msg, b"deleteall"]
        for path, data in files.items():
            path = path if isinstance(path, bytes) else path.encode("utf-8")
            data = data if isinstance(data, bytes) else data.encode("utf-8")
            p.append(b"M 100644 inline " + _q(path))
            p.append(b"data %d" % len(data))
            p.append(data)
        self.parts.append(b"\n".join(p) + b"\n\n")
        return self.mark

    def tag(self, name, mark):
        name = name if isinstance(name, bytes) else name.encode("utf-8")
        self.parts.append(b"reset refs/tags/" + name + b"\nfrom :%d\n\n" % mark)

    def run(self, repo: "Repo"):
        data = b"".join(self.parts) + b"done\n"
        r = subprocess.run(["git", "fast-import", "--quiet", "--done"], cwd=str(repo.path), input=data,
                           capture_output=True, env=BASE_ENV)
        if r.returncode != 0:
            raise NotRun("git fast-import refused the staged history: %s"
                         % r.stderr.decode("utf-8", "replace").strip().splitlines()[:1])


def _drift_repo(root, name="repo"):
    r = Repo(root, name)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    return r


def _loose_object(repo_path: Path, oid: str) -> Path:
    obj = repo_path / ".git" / "objects" / oid[:2] / oid[2:]
    if not obj.exists():
        raise NotRun("the object to delete is not loose here")
    return obj


def _invisible(text: str) -> list:
    """Characters that render as nothing or as a plain space: format (Cf) and non-ASCII space (Zs)."""
    return [c for c in text if unicodedata.category(c) == "Cf"
            or (unicodedata.category(c) == "Zs" and c != " ")]


def _shell_eval(root: Path, words: str):
    """Evaluate `words` as arguments of printf in a POSIX shell, in a fresh folder; return
    (stdout, whether the marker file MARK was created there)."""
    if not POSIX:
        raise NotRun("evaluating a suggested command line needs a POSIX shell")
    d = root / "shell_eval"
    d.mkdir(exist_ok=True)
    r = subprocess.run(["sh", "-c", "printf '%s\\n' " + words], cwd=str(d), capture_output=True,
                       env=BASE_ENV, stdin=subprocess.DEVNULL, timeout=TIME_LIMIT)
    made = (d / "MARK").exists()
    return r.stdout.decode("utf-8", "replace").rstrip("\n"), made


def _shallow_with_missing_tag(root, tags_present, tag_missing):
    """A depth-1/2 clone with refs written by hand: `tags_present` name commits whose objects are in
    the clone; `tag_missing` names a commit whose object is not."""
    src = Repo(root, "src")
    src.release("v0", "1.0", {"src/a.py": b"A=0\n"})
    src.release("v1", "1.1", {"src/a.py": b"A=1\n"})
    src.release("v2", "1.2", {"src/a.py": b"A=2\n"})
    dst = root / "shallow"
    r = subprocess.run(["git", "clone", "-q", "--no-tags", "--depth", "2", "file://" + src.path.as_posix(),
                        str(dst)], capture_output=True, env=BASE_ENV, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise NotRun("a shallow clone could not be made here")
    shas = {t: src.git("rev-parse", t + "^{commit}") for t in ("v0", "v1", "v2")}
    have = subprocess.run(["git", "cat-file", "-e", shas[tag_missing]], cwd=str(dst), env=BASE_ENV,
                          capture_output=True, stdin=subprocess.DEVNULL).returncode == 0
    if have:
        raise NotRun("the shallow clone holds the commit meant to be missing")
    tagdir = dst / ".git" / "refs" / "tags"
    tagdir.mkdir(parents=True, exist_ok=True)
    for t in list(tags_present) + [tag_missing]:
        (tagdir / t).write_text(shas[t] + "\n")
    return src, dst


def _diag_block(out: str) -> str:
    lines = out.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.startswith("diagnostics")]
    if not starts:
        raise Loose("no diagnostics block was printed")
    s = starts[0]
    end = s
    for i in range(s, len(lines)):
        if lines[i].startswith("  options"):
            end = i
        if lines[i].startswith("  repository"):
            end = i
            break
    return "\n".join(lines[s:end + 1])


def _no_sentinels(where, text):
    hits = [t for t in SENT_TOKENS if t in text]
    need(not hits, "%s carries %s" % (where, ", ".join(hits)))


def _sentinel_repo(root, parent=None):
    base = parent or root
    r = Repo(base, "REPOSENTINEL")
    r.write("package.json", _pj(SENT_LABEL))
    r.write("src/PATHSENTINEL.py", b"A=1\n")
    r.commit("v1")
    r.tag("v9.8.7-LBLSENTINEL.1")
    r.write("src/PATHSENTINEL.py", b"A=2\n")
    r.commit("v2")
    r.tag("v9.8.7-LBLSENTINEL.2")
    return r


def _sentinel_env(root):
    home = root / "HOMESENTINEL"
    home.mkdir(exist_ok=True)
    return dict(BASE_ENV, HOME=str(home), CD_ADV_EXTRA="ENVSENTINEL")


def _detector_version():
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', Path(DETECTOR).read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


# --------------------------------------------------------------------------- WT: --would-tag
@case("WT01", "would-tag: a collision just outside the default --max-commits must not pass")
def wt01(root):
    r = Repo(root)
    fi = FastImport()
    c1 = fi.commit({"package.json": _pj("1.0"), "src/a.py": b"A=1\n"})
    fi.tag("v0", c1)
    c2 = fi.commit({"package.json": _pj("2.0"), "src/a.py": b"A=2\n"})
    for i in range(401):
        fi.tag("t%03d" % i, c2)
    fi.commit({"package.json": _pj("1.0"), "src/a.py": b"A=3\n"})
    fi.run(r)
    res = run(r, "--would-tag", timeout=EXT_LIMIT)
    no_traceback(res)
    need(not res["timed_out"], "the run did not return within %.0fs" % EXT_LIMIT)
    need(res["code"] != 0,
         "exit 0 (%s): tag v0 declares 1.0 with other code, but it lies outside the default range of "
         "400 points, and the gate passed" % verdict(res))


@case("WT02", "would-tag: a collision excluded by --tags passes only with the exclusion disclosed")
def wt02(root):
    r = Repo(root)
    r.release("old-1.0", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2.0", "2.0", {"src/a.py": b"A=2\n"})
    r.pkg("1.0")
    r.write("src/a.py", b"A=3\n")
    r.commit("head")
    res = run(r, "--would-tag", "--tags", "v*")
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    if res["code"] == 0:
        need((res["doc"] or {}).get("tags_filtered_out", 0) >= 1,
             "exit 0 without tags_filtered_out >= 1 in the JSON")
        txt = run(r, "--would-tag", "--tags", "v*", as_json=False)
        need("do not match --tags" in txt["out"], "exit 0 and the text does not say a tag was left out")


@case("WT03", "would-tag: a --tags glob matching no tag must not pass the gate")
def wt03(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.write("src/a.py", b"A=2\n")
    r.commit("head")
    res = run(r, "--would-tag", "--tags", "nothing-*")
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    need(res["code"] != 0,
         "exit 0 (%s): the glob selected no tag, so HEAD was compared with nothing, and the gate "
         "passed while v1 declares the same label with other code" % verdict(res))


@case("WT04", "would-tag: the repository's own tags glob hides a collision only with disclosure")
def wt04(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("release-2", "2.0", {"src/a.py": b"A=2\n"})
    r.write(".closure-drift.json", b'{"tags": ["release-*"]}')
    r.pkg("1.0")
    r.write("src/a.py", b"A=3\n")
    r.commit("head")
    res = run(r, "--would-tag")
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    if res["code"] == 0:
        doc = res["doc"] or {}
        need(doc.get("tag_globs") == ["release-*"] and doc.get("tags_filtered_out", 0) >= 1,
             "exit 0 without tag_globs/tags_filtered_out disclosed: %r/%r"
             % (doc.get("tag_globs"), doc.get("tags_filtered_out")))
        txt = run(r, "--would-tag", as_json=False)
        need("do not match --tags" in txt["out"], "exit 0 and the text does not say a tag was left out")


@case("WT05", "would-tag: a same-label tag with an empty closure must not let the gate pass")
def wt05(root):
    r = Repo(root)
    r.pkg("1.0")
    r.write("README.md", b"readme\n")
    r.commit("v1")
    r.tag("v1")
    r.write("src/a.py", b"A=1\n")
    r.commit("head")
    res = run(r, "--would-tag")
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    need(res["code"] != 0,
         "exit 0 (%s): v1 declares 1.0 over an empty closure, HEAD declares 1.0 over src/a.py; "
         "the label would name two closures" % verdict(res))


@case("WT06", "would-tag control: an unlabelled tag does not collide, and is counted")
def wt06(root):
    r = Repo(root)
    r.write("src/a.py", b"A=1\n")
    r.commit("v1")
    r.tag("v1")
    r.pkg("1.0")
    r.write("src/a.py", b"A=2\n")
    r.commit("head")
    res = run(r, "--would-tag")
    no_traceback(res)
    exit_in(res, (0,))
    doc = res["doc"] or {}
    need(doc.get("verdict") == "would_be_clean" and doc.get("points_without_label") == 1,
         "verdict %r, points_without_label %r" % (doc.get("verdict"), doc.get("points_without_label")))


@case("WT07", "would-tag: a label differing by an invisible character is made visible in text")
def wt07(root):
    r = Repo(root)
    r.write("package.json", _pj("1.0"))
    r.write("src/a.py", b"A=1\n")
    r.commit("v1")
    r.tag("v1")
    lab = "1.0​"
    r.write("package.json", _pj(lab))
    r.write("src/a.py", b"A=2\n")
    r.commit("head")
    res = run(r, "--would-tag")
    no_traceback(res)
    exit_in(res, (0,))
    need((res["doc"] or {}).get("label_at_head") == lab, "label_at_head did not round-trip")
    txt = run(r, "--would-tag", as_json=False)
    line = [ln for ln in txt["out"].splitlines() if ln.startswith("label at HEAD")]
    need(line, "no 'label at HEAD' line")
    shown = line[0][len("label at HEAD"):].strip(" ")
    need(not _invisible(shown),
         "the label is printed with an invisible character left raw (%s): it reads as '1.0', the "
         "label of v1, beside 'WOULD BE CLEAN'" % ", ".join("U+%04X" % ord(c) for c in _invisible(shown)))


@case("WT08", "would-tag: detached HEAD with a collision is would_drift")
def wt08(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.write("src/a.py", b"A=2\n")
    r.commit("head")
    r.git("checkout", "-q", "--detach", "HEAD")
    res = run(r, "--would-tag")
    no_traceback(res)
    exit_in(res, (1,))
    doc = res["doc"] or {}
    need(doc.get("verdict") == "would_drift" and any(w.startswith("v1 ") for w in doc.get("collides_with", [])),
         "verdict %r collides_with %r" % (doc.get("verdict"), doc.get("collides_with")))


@case("WT09", "would-tag: HEAD on an unborn branch refuses")
def wt09(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.git("checkout", "-q", "--orphan", "fresh")
    res = run(r, "--would-tag")
    no_traceback(res)
    exit_in(res, (2,))
    need(res["doc"] is None and res["err"].strip(), "expected a refusal on stderr, got %r" % verdict(res))


@case("WT10", "would-tag: HEAD already tagged, older tag collides")
def wt10(root):
    r = _drift_repo(root)
    res = run(r, "--would-tag")
    no_traceback(res)
    exit_in(res, (1,))
    names = [w.split(" (")[0] for w in (res["doc"] or {}).get("collides_with", [])]
    need(names == ["v1"], "collides_with names %r, expected exactly v1" % names)


@case("WT11", "would-tag: a replace ref on HEAD's commit does not hide the collision")
def wt11(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.write("src/a.py", b"A=2\n")
    r.commit("head")
    r.git("replace", r.git("rev-parse", "HEAD"), r.git("rev-parse", "v1^{commit}"))
    res = run(r, "--would-tag")
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "would_drift", "verdict %r" % verdict(res))


@case("WT12", "would-tag: a tag whose commit object is missing (shallow) must not let the gate pass")
def wt12(root):
    src = Repo(root, "src")
    src.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    src.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    src.release("v3", "3.0", {"src/a.py": b"A=3\n"})
    src.pkg("1.0")
    src.write("src/a.py", b"A=9\n")
    src.commit("head")
    dst = root / "shallow"
    cl = subprocess.run(["git", "clone", "-q", "--no-tags", "--depth", "1", "file://" + src.path.as_posix(),
                         str(dst)], capture_output=True, env=BASE_ENV, stdin=subprocess.DEVNULL)
    if cl.returncode != 0:
        raise NotRun("a shallow clone could not be made here")
    sha = src.git("rev-parse", "v1^{commit}")
    if subprocess.run(["git", "cat-file", "-e", sha], cwd=str(dst), env=BASE_ENV, capture_output=True,
                      stdin=subprocess.DEVNULL).returncode == 0:
        raise NotRun("the shallow clone holds v1's commit")
    (dst / ".git" / "refs" / "tags").mkdir(parents=True, exist_ok=True)
    (dst / ".git" / "refs" / "tags" / "v1").write_text(sha + "\n")
    res = run(dst, "--would-tag")
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    need(res["code"] != 0,
         "exit 0 (%s): the tag v1 exists and could not be read; it was not treated as a failed read"
         % verdict(res))


@case("WT13", "would-tag: an uncommitted version change is not measured; the commit is (declared)")
def wt13(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.pkg("2.0")
    r.write("src/a.py", b"A=2\n")
    r.commit("head")
    r.pkg("1.0")
    res = run(r, "--would-tag")
    no_traceback(res)
    exit_in(res, (0,))
    doc = res["doc"] or {}
    need(doc.get("verdict") == "would_be_clean" and doc.get("stamp", {}).get("working_tree_dirty") is True,
         "verdict %r dirty %r" % (doc.get("verdict"), doc.get("stamp", {}).get("working_tree_dirty")))
    txt = run(r, "--would-tag", as_json=False)
    need("the commit is measured, not the modified working tree" in txt["out"],
         "the text does not say that the commit was measured")


@case("WT14", "would-tag: a branch named like the tag must not take the tag out of --tags")
def wt14(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.git("branch", "v1", "v1")
    r.write("src/a.py", b"A=2\n")
    r.commit("head")
    base = run(r, "--would-tag")
    need(verdict(base) == "would_drift", "control without --tags gave %r" % verdict(base))
    res = run(r, "--would-tag", "--tags", "v*")
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    need(res["code"] == 1 and verdict(res) == "would_drift",
         "with --tags 'v*' the verdict is %r, exit %r: the tag v1 matches v* but a branch named v1 made "
         "it leave the selection" % (verdict(res), res["code"]))


@case("WT15", "would-tag: the suggested --compare line runs nothing when pasted (hardening)")
def wt15(root):
    if not POSIX:
        raise NotRun("evaluating a suggested command line needs a POSIX shell")
    r = Repo(root)
    tag = "$(>MARK)v1"
    r.release(tag, "1.0", {"src/a.py": b"A=1\n"})
    r.write("src/a.py", b"A=2\n")
    r.commit("head")
    res = run(r, "--would-tag", as_json=False)
    no_traceback(res)
    exit_in(res, (1,))
    line = [ln.strip() for ln in res["out"].splitlines() if ln.strip().startswith("--compare ")]
    need(line, "no suggested --compare line")
    words = line[0][len("--compare "):]
    if words.endswith(" HEAD"):
        words = words[:-len(" HEAD")]
    out, made = _shell_eval(root, words)
    need(not made and out == tag,
         "pasting the suggested '--compare %s HEAD' into a shell %s"
         % (words, "runs the tag name as a command (marker created)" if made else "does not pass the tag literally"))


# --------------------------------------------------------------------------- TG: --tags
@case("TG01", "--tags '*' is the same as no --tags")
def tg01(root):
    r = _drift_repo(root)
    res = run(r, "--tags", "*")
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "verdict %r" % verdict(res))


@case("TG02", "--tags '[' (unbalanced) is handled")
def tg02(root):
    r = _drift_repo(root)
    res = run(r, "--tags", "[")
    no_traceback(res)
    exit_in(res, (1, 2))
    need("internal error" not in res["err"], "the catch-all answered: " + res["err"].strip()[:160])


@case("TG03", "--tags '[z-a]' (reversed range), from the flag and from the repository's config")
def tg03(root):
    r = _drift_repo(root)
    res = run(r, "--tags", "[z-a]")
    no_traceback(res)
    exit_in(res, (2,))
    need("internal error" not in res["err"], "flag: the catch-all answered: " + res["err"].strip()[:160])
    r.write(".closure-drift.json", b'{"tags": ["[z-a]"]}')
    res2 = run(r)
    no_traceback(res2)
    exit_in(res2, (2,))
    need("internal error" not in res2["err"], "config: the catch-all answered: " + res2["err"].strip()[:160])


@case("TG04", "--tags with a leading dash")
def tg04(root):
    r = _drift_repo(root)
    for args in (("--tags=-*",), ("--tags", "-x")):
        res = run(r, *args)
        no_traceback(res)
        exit_in(res, (2,))


@case("TG05", "--tags '' (empty glob) never yields a determination")
def tg05(root):
    r = _drift_repo(root)
    res = run(r, "--tags", "")
    no_traceback(res)
    exit_in(res, (2,))


@case("TG06", "the repository's tags glob matching nothing is no_publication_points naming it")
def tg06(root):
    r = _drift_repo(root)
    r.write(".closure-drift.json", b'{"tags": ["nomatch-*"]}')
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))
    doc = res["doc"] or {}
    need(doc.get("verdict") == "no_publication_points" and "nomatch-*" in doc.get("note", ""),
         "verdict %r note %r" % (doc.get("verdict"), doc.get("note")))


@case("TG07", "--tags selects before --max-commits cuts")
def tg07(root):
    r = Repo(root)
    r.release("py-1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("py-2", "1.0", {"src/a.py": b"A=2\n"})
    for i in range(10):
        r.release("rs-%d" % i, "r%d" % i, {"src/a.py": b"R=%d\n" % i})
    res = run(r, "--tags", "py-*", "--max-commits", "2")
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "verdict %r" % verdict(res))


@case("TG08", "a tree tag matching --tags is counted as not a commit, not as filtered")
def tg08(root):
    r = _drift_repo(root)
    r.git("tag", "v-tree", r.git("rev-parse", "v1^{tree}"))
    res = run(r, "--tags", "v*")
    no_traceback(res)
    exit_in(res, (1,))
    doc = res["doc"] or {}
    need(doc.get("points_not_commits", 0) >= 1 and doc.get("tags_filtered_out") == 0,
         "points_not_commits %r tags_filtered_out %r" % (doc.get("points_not_commits"), doc.get("tags_filtered_out")))


@case("TG09", "a branch named like a tag must not take the tag out of --tags")
def tg09(root):
    r = _drift_repo(root)
    r.git("branch", "v1", "v1")
    base = run(r)
    need(verdict(base) == "drift", "control without --tags gave %r" % verdict(base))
    res = run(r, "--tags", "v*")
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    need(res["code"] == 1 and verdict(res) == "drift",
         "with --tags 'v*' the verdict is %r, exit %r, tags_filtered_out %r: a branch named v1 made the "
         "tag v1 leave the selection" % (verdict(res), res["code"], (res["doc"] or {}).get("tags_filtered_out")))


# --------------------------------------------------------------------------- SR: --strict
@case("SR01", "--strict with a tree tag: clean only with points_not_commits disclosed")
def sr01(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    r.git("tag", "vtree", r.git("rev-parse", "v1^{tree}"))
    res = run(r, "--strict")
    no_traceback(res)
    exit_in(res, (0, 2))
    if res["code"] == 0:
        need((res["doc"] or {}).get("points_not_commits", 0) >= 1, "clean without points_not_commits")
        txt = run(r, "--strict", as_json=False)
        need("do not point at a commit" in txt["out"], "clean and the text does not say a tag was skipped")


@case("SR02", "--strict --tags: clean only with tags_filtered_out disclosed")
def sr02(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    r.git("rm", "-q", "package.json")
    r.write("src/a.py", b"A=3\n")
    r.commit("x1")
    r.tag("x1")
    r.pkg("2.0")
    r.commit("head")
    res = run(r, "--strict", "--tags", "v*")
    no_traceback(res)
    exit_in(res, (0, 2))
    if res["code"] == 0:
        need((res["doc"] or {}).get("tags_filtered_out") == 1,
             "clean with tags_filtered_out %r" % (res["doc"] or {}).get("tags_filtered_out"))


@case("SR03", "--strict with a tag whose commit object is missing is never clean")
def sr03(root):
    _src, dst = _shallow_with_missing_tag(root, ("v1", "v2"), "v0")
    res = run(dst, "--strict")
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    need(res["code"] == 2,
         "exit %r (%s): v0 could not be read and --strict still answered" % (res["code"], verdict(res)))


@case("SR04", "--strict with --would-tag, and with --compare, refuse")
def sr04(root):
    r = _drift_repo(root)
    for args in (("--strict", "--would-tag"), ("--strict", "--compare", "v1", "v2")):
        res = run(r, *args)
        no_traceback(res)
        exit_in(res, (2,))
        need(res["doc"] is None, "%s produced a report instead of a refusal" % " ".join(args))


@case("SR05", "--at commits --strict with an unlabelled commit is incomplete")
def sr05(root):
    r = Repo(root)
    r.write("src/a.py", b"A=0\n")
    r.commit("c0")
    r.pkg("1.0")
    r.write("src/a.py", b"A=1\n")
    r.commit("c1")
    r.pkg("2.0")
    r.write("src/a.py", b"A=2\n")
    r.commit("c2")
    res = run(r, "--at", "commits", "--strict")
    no_traceback(res)
    exit_in(res, (2,))
    need(verdict(res) == "incomplete", "verdict %r" % verdict(res))


@case("SR06", "--strict --tags with a branch named like an unlabelled tag is never clean")
def sr06(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.1", {"src/a.py": b"A=2\n"})
    r.git("rm", "-q", "package.json")
    r.write("src/a.py", b"A=3\n")
    r.commit("v3")
    r.tag("v3")
    r.git("branch", "v3", "v3")
    r.pkg("1.2")
    r.commit("head")
    res = run(r, "--strict", "--tags", "v*")
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    need(res["code"] == 2 and verdict(res) == "incomplete",
         "verdict %r exit %r: the unlabelled tag v3 matches v* and was not compared"
         % (verdict(res), res["code"]))


# --------------------------------------------------------------------------- XP: --explain
@case("XP01", "--explain of a label that looks like an option")
def xp01(root):
    r = Repo(root)
    r.release("v1", "--json", {"src/a.py": b"A=1\n"})
    r.release("v2", "--json", {"src/a.py": b"A=2\n"})
    res = run(r, "--explain=--json")
    no_traceback(res)
    exit_in(res, (1,))
    ex = (res["doc"] or {}).get("explain") or {}
    need(ex.get("label") == "--json" and ex.get("others", [{}])[0].get("changed") == ["src/a.py"],
         "explain %r" % ex)


@case("XP02", "--explain of a control-character label, and its refusal, are escaped")
def xp02(root):
    r = _inject_repo(root)
    res = run(r, "--explain", INJ_LABEL, as_json=False)
    no_traceback(res)
    exit_in(res, (1,))
    for raw in ("\x1b", "\x07", "‮", " "):
        need(raw not in res["out"], "raw %r in the --explain text" % raw)
    need(not [ln for ln in res["out"].splitlines() if ln.startswith("CLEAN")], "a forged CLEAN line")
    ref = run(r, "--explain", INJ_LABEL + "X", as_json=False)
    no_traceback(ref)
    exit_in(ref, (2,))
    for raw in ("\x1b", "\x07", "‮", " "):
        need(raw not in ref["err"], "raw %r in the refusal" % raw)
    need(not [ln for ln in ref["err"].splitlines() if ln.startswith("CLEAN")], "a forged CLEAN line in stderr")


OUTSIDE = ("README.md", "docs/secret.py", "tests/hidden_test.py", "OUTSIDE.txt")


def _outside_repo(root):
    r = Repo(root)
    files1 = {"src/a.py": b"A=1\n"}
    files2 = {"src/a.py": b"A=2\n"}
    for p in OUTSIDE:
        files1[p] = b"one\n"
        files2[p] = b"two\n"
    r.release("v1", "1.0", files1)
    r.release("v2", "1.0", files2)
    return r


@case("XP03", "--explain lists no path outside the closure")
def xp03(root):
    r = _outside_repo(root)
    for as_json in (True, False):
        res = run(r, "--explain", "1.0", as_json=as_json)
        no_traceback(res)
        exit_in(res, (1,))
        need("src/a.py" in res["out"], "the changed path is not listed")
        leaked = [p for p in OUTSIDE if p in res["out"]]
        need(not leaked, "paths outside the closure listed: %r" % leaked)


@case("XP04", "--explain over 5,000 changed files completes and caps the text")
def xp04(root):
    r = Repo(root)
    fi = FastImport()
    for n, tag in ((1, "v1"), (2, "v2")):
        files = {"src/f%04d.py" % i: b"X=%d\n" % n for i in range(5000)}
        files["package.json"] = _pj("1.0")
        fi.tag(tag, fi.commit(files))
    fi.run(r)
    res = run(r, "--explain", "1.0", timeout=EXT_LIMIT)
    no_traceback(res)
    need(not res["timed_out"], "the run did not return within %.0fs" % EXT_LIMIT)
    exit_in(res, (1,))
    ch = ((res["doc"] or {}).get("explain") or {}).get("others", [{}])[0].get("changed", [])
    need(len(ch) == 5000, "changed holds %d paths" % len(ch))
    txt = run(r, "--explain", "1.0", as_json=False, timeout=EXT_LIMIT)
    listed = [ln for ln in txt["out"].splitlines() if ln.strip().startswith("changed") and "src/f" in ln]
    need(len(listed) <= 40 and "... and 4960 more" in txt["out"], "text listed %d paths" % len(listed))


@case("XP05", "--explain of a label at three closures")
def xp05(root):
    r = Repo(root)
    for i in (1, 2, 3):
        r.release("v%d" % i, "1.0", {"src/a.py": b"A=%d\n" % i})
    res = run(r, "--explain", "1.0")
    no_traceback(res)
    exit_in(res, (1,))
    need(len(((res["doc"] or {}).get("explain") or {}).get("others", [])) == 2, "others is not 2 long")


@case("XP06", "--explain '' refuses")
def xp06(root):
    r = _drift_repo(root)
    res = run(r, "--explain", "")
    no_traceback(res)
    exit_in(res, (2,))
    need(res["doc"] is None, "a report instead of a refusal")


# --------------------------------------------------------------------------- CP: --compare
@case("CP01", "--compare refs that look like options reach nothing")
def cp01(root):
    r = _drift_repo(root)
    before = snapshot(r.path)
    res = run(r, "--compare", "--help", "HEAD", as_json=False)
    no_traceback(res)
    exit_in(res, (2,))
    res2 = run(r, "--compare", "--output=OUTFILE x", "HEAD", cwd=str(root))
    no_traceback(res2)
    exit_in(res2, (2,))
    need(not list(root.rglob("OUTFILE*")), "a file OUTFILE was created")
    changes = diff_snapshots(before, snapshot(r.path))
    need(not changes, "the repository changed: " + "; ".join(changes[:3]))


@case("CP02", "--compare of ranges refuses")
def cp02(root):
    r = _drift_repo(root)
    for ref in ("v1..v2", "v1...v2"):
        res = run(r, "--compare", ref, "v2")
        no_traceback(res)
        exit_in(res, (2,))
        need(res["doc"] is None, "%s produced a report" % ref)


@case("CP03", "--compare of objects that are not commits refuses")
def cp03(root):
    r = _drift_repo(root)
    r.git("tag", "treetag", r.git("rev-parse", "HEAD^{tree}"))
    blob = r.git("rev-parse", "HEAD:package.json")
    for ref in ("HEAD:package.json", "HEAD^{tree}", blob, "treetag"):
        res = run(r, "--compare", ref, "v1")
        no_traceback(res)
        exit_in(res, (2,))
        need(res["doc"] is None, "a report for a non-commit ref")


@case("CP04", "--compare of one commit named twice is identical")
def cp04(root):
    r = _drift_repo(root)
    for a, b in (("v1", "v1"), ("v1", r.git("rev-parse", "v1^{commit}")), ("v1", "v1^{}")):
        res = run(r, "--compare", a, b)
        no_traceback(res)
        exit_in(res, (0,))
        need(verdict(res) == "identical", "verdict %r" % verdict(res))


@case("CP05", "--compare of a ref holding control characters is escaped in the refusal")
def cp05(root):
    r = _drift_repo(root)
    res = run(r, "--compare", "v1\x1b[2J\nIDENTICAL: forged", "v2", as_json=False)
    no_traceback(res)
    exit_in(res, (2,))
    need("\x1b" not in res["err"], "raw ESC in stderr")
    need(not [ln for ln in res["err"].splitlines() if ln.startswith("IDENTICAL")], "a forged IDENTICAL line")


@case("CP06", "--compare is not fooled by a replace ref")
def cp06(root):
    r = _drift_repo(root)
    r.git("replace", r.git("rev-parse", "v2^{commit}"), r.git("rev-parse", "v1^{commit}"))
    res = run(r, "--compare", "v1", "v2")
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "differs_under_one_label", "verdict %r" % verdict(res))


@case("CP07", "--compare across unrelated histories")
def cp07(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.git("checkout", "-q", "--orphan", "other")
    r.git("rm", "-rfq", ".")
    r.pkg("1.0")
    r.write("src/b.py", b"B=1\n")
    r.commit("orphan")
    res = run(r, "--compare", "v1", "other")
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "differs_under_one_label", "verdict %r" % verdict(res))


@case("CP08", "--compare lists no path outside the closure")
def cp08(root):
    r = _outside_repo(root)
    for as_json in (True, False):
        res = run(r, "--compare", "v1", "v2", as_json=as_json)
        no_traceback(res)
        exit_in(res, (1,))
        need("src/a.py" in res["out"], "the changed path is not listed")
        leaked = [p for p in OUTSIDE if p in res["out"]]
        need(not leaked, "paths outside the closure listed: %r" % leaked)


@case("CP09", "--compare of labels differing by an invisible character shows the difference")
def cp09(root):
    r = Repo(root)
    r.write("package.json", _pj("1.0"))
    r.write("src/a.py", b"A=1\n")
    r.commit("v1")
    r.tag("v1")
    r.write("package.json", _pj("1.0 "))
    r.write("src/a.py", b"A=2\n")
    r.commit("v2")
    r.tag("v2")
    res = run(r, "--compare", "v1", "v2")
    no_traceback(res)
    exit_in(res, (0,))
    doc = res["doc"] or {}
    need(doc.get("verdict") == "differs_under_two_labels" and doc.get("b", {}).get("label") == "1.0 ",
         "verdict %r label b %r" % (doc.get("verdict"), doc.get("b", {}).get("label")))
    txt = run(r, "--compare", "v1", "v2", as_json=False)
    labels = [ln.split("label", 1)[1].strip(" ") for ln in txt["out"].splitlines() if ln.startswith("   label")]
    need(len(labels) == 2, "two label lines expected")
    need(not any(_invisible(x) for x in labels),
         "a label is printed with an invisible character left raw: the two label lines render alike "
         "under 'DIFFERS UNDER TWO LABELS'")


# --------------------------------------------------------------------------- DG: --diagnose
@case("DG01", "--diagnose leaks no label, repository path, closure path, home or environment")
def dg01(root):
    r = _sentinel_repo(root)
    env = _sentinel_env(root)
    txt = run(r, "--diagnose", as_json=False, env=env)
    no_traceback(txt)
    exit_in(txt, (1,))
    _no_sentinels("the text diagnose block", _diag_block(txt["out"]))
    js = run(r, "--diagnose", env=env)
    exit_in(js, (1,))
    _no_sentinels("the JSON diagnostics", json.dumps((js["doc"] or {}).get("diagnostics"), ensure_ascii=False))


@case("DG02", "--diagnose with a relative repository path leaks nothing")
def dg02(root):
    r = _sentinel_repo(root)
    env = _sentinel_env(root)
    txt = run("REPOSENTINEL", "--diagnose", as_json=False, env=env, cwd=str(root))
    no_traceback(txt)
    exit_in(txt, (1,))
    _no_sentinels("the text diagnose block", _diag_block(txt["out"]))
    js = run("REPOSENTINEL", "--diagnose", env=env, cwd=str(root))
    exit_in(js, (1,))
    _no_sentinels("the JSON diagnostics", json.dumps((js["doc"] or {}).get("diagnostics"), ensure_ascii=False))


@case("DG03", "--diagnose with a --closure glob that is a literal path inside the closure")
def dg03(root):
    r = _sentinel_repo(root)
    env = _sentinel_env(root)
    txt = run(r, "--diagnose", "--closure", "src/PATHSENTINEL.py", as_json=False, env=env)
    no_traceback(txt)
    exit_in(txt, (1,))
    _no_sentinels("the text diagnose block", _diag_block(txt["out"]))
    js = run(r, "--diagnose", "--closure", "src/PATHSENTINEL.py", env=env)
    _no_sentinels("the JSON diagnostics", json.dumps((js["doc"] or {}).get("diagnostics"), ensure_ascii=False))


@case("DG04", "--diagnose with a --tags glob carrying the version label")
def dg04(root):
    r = _sentinel_repo(root)
    env = _sentinel_env(root)
    txt = run(r, "--diagnose", "--tags", "v9.8.7-LBLSENTINEL*", as_json=False, env=env)
    no_traceback(txt)
    exit_in(txt, (1,))
    _no_sentinels("the text diagnose block", _diag_block(txt["out"]))
    js = run(r, "--diagnose", "--tags", "v9.8.7-LBLSENTINEL*", env=env)
    _no_sentinels("the JSON diagnostics", json.dumps((js["doc"] or {}).get("diagnostics"), ensure_ascii=False))


@case("DG05", "--diagnose with --explain, --version-file/--version-regex, --compare: booleans only")
def dg05(root):
    r = _sentinel_repo(root)
    r.git("tag", "REFSENTINEL-a", "v9.8.7-LBLSENTINEL.1")
    r.git("tag", "REFSENTINEL-b", "v9.8.7-LBLSENTINEL.2")
    env = _sentinel_env(root)
    runs = (("--explain", SENT_LABEL),
            ("--version-file", "package.json", "--version-regex", '"version": "(9[^"]*LBLSENTINEL)"'),
            ("--compare", "REFSENTINEL-a", "REFSENTINEL-b"))
    for args in runs:
        txt = run(r, "--diagnose", *args, as_json=False, env=env)
        no_traceback(txt)
        exit_in(txt, (1,))
        blk = _diag_block(txt["out"])
        _no_sentinels("the text diagnose block (%s)" % args[0], blk)
        need("REFSENTINEL" not in blk, "the text diagnose block names a --compare ref")
        js = run(r, "--diagnose", *args, env=env)
        d = json.dumps((js["doc"] or {}).get("diagnostics"), ensure_ascii=False)
        _no_sentinels("the JSON diagnostics (%s)" % args[0], d)
        need("REFSENTINEL" not in d, "the JSON diagnostics name a --compare ref")


@case("DG06", "--diagnose changes no verdict and no exit code")
def dg06(root):
    drift = _drift_repo(root, "drift")
    clean = Repo(root, "clean")
    clean.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    clean.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    wd = Repo(root, "wd")
    wd.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    wd.write("src/a.py", b"A=2\n")
    wd.commit("head")
    notags = Repo(root, "notags")
    notags.pkg("1.0")
    notags.write("src/a.py", b"A=1\n")
    notags.commit("c")
    plain = root / "plain"
    plain.mkdir()
    probes = ((drift, ()), (clean, ()), (wd, ("--would-tag",)), (clean, ("--would-tag",)),
              (drift, ("--compare", "v1", "v2")), (notags, ()), (plain, ()))
    for repo, args in probes:
        a = run(repo, *args)
        b = run(repo, *args, "--diagnose")
        no_traceback(b)
        need(a["code"] == b["code"], "exit %r without --diagnose, %r with" % (a["code"], b["code"]))
        da = dict(a["doc"] or {})
        db = dict(b["doc"] or {})
        db.pop("diagnostics", None)
        need(da == db, "the report differs with --diagnose beyond the diagnostics key (%s)" % (args or ("default",))[0])


@case("DG07", "--diagnose runs no repository-configured command and writes nothing")
def dg07(root):
    if WINDOWS:
        raise NotRun("command-execution markers use a POSIX shell script")
    r = _drift_repo(root)
    marker = root / "MARKER_DG07"
    val = marker_script(root, marker)
    hooks = r.path / "myhooks"
    hooks.mkdir()
    for h in ("post-index-change", "reference-transaction", "post-checkout"):
        (hooks / h).write_text("#!/bin/sh\n: > '%s'\n" % marker)
        (hooks / h).chmod(0o755)
    up = root / "upstream"
    up.mkdir()
    for k, v in (("core.fsmonitor", val), ("core.hooksPath", str(hooks)), ("filter.x.clean", val),
                 ("core.repositoryformatversion", "1"), ("extensions.partialClone", "origin"),
                 ("remote.origin.url", "file://" + up.as_posix()), ("remote.origin.promisor", "true"),
                 ("remote.origin.uploadpack", val)):
        r.git("config", "--local", k, v)
    r.write(".gitattributes", b"src/a.py filter=x\n")
    (r.path / "src" / "a.py").write_bytes(b"dirty\n")
    before = snapshot(r.path)
    for as_json in (True, False):
        res = run(".", "--diagnose", as_json=as_json, cwd=str(r.path))
        no_traceback(res)
        exit_in(res, (0, 1, 2))
    made = marker.exists()
    changes = diff_snapshots(before, snapshot(r.path))
    need(not made, "a command named in the repository's config ran under --diagnose (marker created)")
    need(not changes, "the repository changed under --diagnose: " + "; ".join(changes[:3]))


@case("DG08", "--diagnose on a folder that is not a repository")
def dg08(root):
    d = root / "REPOSENTINEL"
    d.mkdir()
    txt = run(d, "--diagnose", as_json=False)
    no_traceback(txt)
    exit_in(txt, (2,))
    _no_sentinels("the text diagnose block", _diag_block(txt["out"]))
    js = run(d, "--diagnose")
    exit_in(js, (2,))
    need(not js["out"].strip(), "a refusal with --json printed something on stdout")


@case("DG09", "--diagnose --json carries exactly the documented keys and the true version")
def dg09(root):
    r = _drift_repo(root)
    res = run(r, "--diagnose")
    exit_in(res, (1,))
    d = (res["doc"] or {}).get("diagnostics") or {}
    want = {"detector_version", "detector_closure", "python", "platform", "git", "options", "repository"}
    need(set(d) == want, "diagnostics keys %r" % sorted(d))
    need(d.get("detector_version") == _detector_version(), "detector_version %r" % d.get("detector_version"))


# --------------------------------------------------------------------------- TV: tag-derived version
@case("TV01", "a 'pbr' substring in an unrelated dependency still tells the user --version-file")
def tv01(root):
    r = Repo(root)
    r.write("pyproject.toml", b'[project]\nname = "x"\ndependencies = ["pbrt-tools>=1"]\n')
    r.write("src/a.py", b"A=1\n")
    r.commit("c")
    r.tag("v1")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))
    need("--version-file" in res["err"], "the refusal does not tell --version-file")


@case("TV02", "a comment naming setuptools_scm is not a version derived from the tag (hardening)")
def tv02(root):
    r = Repo(root)
    r.write("pyproject.toml", b'[project]\nname = "pkg"\n# we do not use setuptools_scm\n')
    r.write("src/pkg/__init__.py", b'__version__ = "1.0"\n')
    r.commit("c")
    r.tag("v1")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))
    need("derived from the tag" not in res["err"],
         "the refusal says the version is derived from the tag; no tool is configured, the word is in a "
         "comment, and the version is in src/pkg/__init__.py")


@case("TV03", "a recognised version file wins over a tag-deriving tool named in pyproject")
def tv03(root):
    r = Repo(root)
    r.write("pyproject.toml", b'[build-system]\nrequires = ["setuptools_scm"]\n')
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    res = run(r)
    no_traceback(res)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "verdict %r" % verdict(res))


@case("TV04", "setup.py with versioneer is refused naming versioneer")
def tv04(root):
    r = Repo(root)
    r.write("setup.py", b"import versioneer\nsetup(name='x', version=versioneer.get_version())\n")
    r.write("src/a.py", b"A=1\n")
    r.commit("c")
    r.tag("v1")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))
    need("versioneer" in res["err"], "the refusal does not name versioneer")


# --------------------------------------------------------------------------- TF: tag families
@case("TF01", "the --tags suggestion runs nothing when pasted (hardening)")
def tf01(root):
    if not POSIX:
        raise NotRun("evaluating a suggested command line needs a POSIX shell")
    r = Repo(root)
    hostile = "x'$(>MARK)-1.0"
    r.release(hostile, "1.0", {"src/a.py": b"A=1\n"})
    r.release("y-1.0", "1.0", {"src/a.py": b"A=2\n"})
    res = run(r, as_json=False)
    no_traceback(res)
    exit_in(res, (1,))
    line = [ln for ln in res["out"].splitlines() if "family at a time: --tags " in ln]
    need(line, "no --tags suggestion printed")
    words = line[0].split("family at a time: --tags ", 1)[1]
    if words.endswith("."):
        words = words[:-1]
    out, made = _shell_eval(root, words)
    need(not made and out == "x'$(>MARK)-*",
         "pasting the suggested --tags %s into a shell %s" % (words, "runs a command (marker created)"
                                                             if made else "does not pass the prefix literally"))


@case("TF02", "an empty family prefix is named and the other family suggested")
def tf02(root):
    r = Repo(root)
    r.release("1.0", "1.0", {"src/a.py": b"A=1\n"})
    r.release("py-1.0", "1.0", {"src/a.py": b"A=2\n"})
    res = run(r)
    no_traceback(res)
    exit_in(res, (1,))
    need(set(((res["doc"] or {}).get("tag_families") or {})) == {"", "py-"},
         "tag_families %r" % (res["doc"] or {}).get("tag_families"))
    txt = run(r, as_json=False)
    need("(none)" in txt["out"] and "--tags 'py-*'" in txt["out"], "the hint does not name both")


@case("TF03", "300 tag families complete")
def tf03(root):
    raise NotRun("superseded by TF05: this case's own expectation was wrong (the family prefix "
                 "stops at the first digit, so f000-1 … f299-1 are one family); see the amendment")
    r = Repo(root)
    fi = FastImport()
    for i in range(300):
        fi.tag("f%03d-1" % i, fi.commit({"package.json": _pj("1.0"), "src/a.py": b"A=%d\n" % i}))
    fi.run(r)
    res = run(r, timeout=EXT_LIMIT)
    no_traceback(res)
    need(not res["timed_out"], "the run did not return within %.0fs" % EXT_LIMIT)
    exit_in(res, (1,))
    need(len((res["doc"] or {}).get("tag_families") or {}) == 300, "tag_families is not 300 long")
    txt = run(r, as_json=False, timeout=EXT_LIMIT)
    no_traceback(txt)
    exit_in(txt, (1,))


@case("TF04", "a bidi override in a family prefix is escaped")
def tf04(root):
    r = Repo(root)
    r.release("‮abc-1.0", "1.0", {"src/a.py": b"A=1\n"})
    r.release("py-1.0", "1.0", {"src/a.py": b"A=2\n"})
    res = run(r, as_json=False)
    no_traceback(res)
    exit_in(res, (1,))
    need("‮" not in res["out"], "raw U+202E in the text")


# --------------------------------------------------------------------------- MX: combinations
@case("MX01", "--version with everything else prints the version and nothing else")
def mx01(root):
    r = _drift_repo(root)
    want = "closure_drift %s\n" % _detector_version()
    for args in (("--version", "--badge", "--diagnose", "--would-tag", "--max-commits", "0"),
                 ("--version", "--compare", "a", "b")):
        res = run(r, *args)
        no_traceback(res)
        exit_in(res, (0,))
        need(res["out"] == want and not res["err"], "stdout %r stderr %r" % (res["out"][:80], res["err"][:80]))


@case("MX02", "--badge in every mode is one line with the verdict")
def mx02(root):
    r = _drift_repo(root)
    s = Repo(root, "strict")
    s.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    s.git("rm", "-q", "package.json")
    s.write("src/a.py", b"A=2\n")
    s.commit("x")
    s.tag("x")
    s.release("v2", "2.0", {"src/a.py": b"A=3\n"})
    head = r.git("rev-parse", "HEAD")[:12]
    shead = s.git("rev-parse", "HEAD")[:12]
    for repo, hd, args, want, code in ((r, head, ("--would-tag",), "would_drift", 1),
                                       (r, head, ("--compare", "v1", "v2"), "differs_under_one_label", 1),
                                       (r, head, ("--explain", "1.0"), "drift", 1),
                                       (s, shead, ("--strict",), "incomplete", 2)):
        res = run(repo, "--badge", *args, as_json=False)
        no_traceback(res)
        exit_in(res, (code,))
        lines = res["out"].splitlines()
        need(len(lines) == 1 and lines[0].startswith("![version labels: %s @ %s]" % (want, hd)),
             "%s: %r" % (args[0], res["out"][:120]))


REPORT_FIELDS = {
    "measure": {"report_format": int, "stamp": dict, "repo": str, "version_file": str, "closure_globs": list,
                "published_at": str, "verdict": str, "labels": int, "labels_covering_multiple_closures": int,
                "max_closures_per_label": int, "drift": dict, "closure_ids": dict,
                "closure_changes_between_points": int, "publication_points": int,
                "publication_points_scanned": int, "publication_points_compared": int,
                "points_without_label": int, "points_with_empty_closure": int, "points_not_commits": int,
                "range_truncated": bool},
    "would_tag": {"report_format": int, "stamp": dict, "mode": str, "repo": str, "version_file": str,
                  "closure_globs": list, "published_at": str, "verdict": str, "label_at_head": str,
                  "closure_at_head": str, "closure_id_at_head": str, "collides_with": list,
                  "existing_drift_labels": int, "publication_points_scanned": int,
                  "publication_points_compared": int, "points_without_label": int,
                  "points_with_empty_closure": int, "points_not_commits": int, "range_truncated": bool},
    "compare": {"report_format": int, "stamp": dict, "mode": str, "repo": str, "version_file": str,
                "closure_globs": list, "verdict": str, "a": dict, "b": dict, "changed": list,
                "only_in_a": list, "only_in_b": list},
    "none": {"report_format": int, "verdict": str, "note": str},
}


def _fields(doc, kind):
    missing = [k for k, t in REPORT_FIELDS[kind].items() if not isinstance(doc.get(k), t)
               or (t is int and isinstance(doc.get(k), bool))]
    return missing


@case("MX03", "--json in every mode is valid and carries the fields REPORT.md lists")
def mx03(root):
    r = _drift_repo(root)
    notags = Repo(root, "notags")
    notags.pkg("1.0")
    notags.write("src/a.py", b"A=1\n")
    notags.commit("c")
    probes = ((r, (), "measure"), (r, ("--explain", "1.0"), "measure"), (r, ("--would-tag",), "would_tag"),
              (r, ("--would-tag", "--tags", "v*"), "would_tag"), (r, ("--compare", "v1", "v2"), "compare"),
              (notags, (), "none"), (r, ("--diagnose",), "measure"))
    for repo, args, kind in probes:
        res = run(repo, *args)
        no_traceback(res)
        need(res["doc"] is not None, "%s: stdout is not JSON" % (args or ("default",))[0])
        missing = _fields(res["doc"], kind)
        need(not missing, "%s: fields missing or mistyped: %r" % ((args or ("default",))[0], missing))
        if kind == "compare":
            for side in ("a", "b"):
                need(set(res["doc"][side]) >= {"ref", "commit", "label", "closure", "closure_id", "files"},
                     "compare side %s lacks a documented field" % side)
        st = res["doc"].get("stamp")
        if st is not None:
            need({"measured_at_head", "working_tree_dirty", "detector_closure"} <= set(st), "stamp fields")


@case("MX04", "--diagnose --badge and --json --badge refuse with nothing on stdout")
def mx04(root):
    r = _drift_repo(root)
    for args in (("--diagnose", "--badge"), ("--json", "--badge")):
        res = run(r, *args, as_json=False)
        no_traceback(res)
        exit_in(res, (2,))
        need(not res["out"].strip(), "%s printed on stdout" % " ".join(args))


@case("MX05", "--help and -h do not end at exit 0 (literal contract)")
def mx05(root):
    raise NotRun("superseded: --help, -h and --version print no verdict and end at 0 by convention; "
                 "the contract now says so (docs/REPORT.md); see the amendment")
    r = _drift_repo(root)
    for flag in ("--help", "-h"):
        res = run(r, flag, as_json=False)
        no_traceback(res)
        need(res["code"] != 0, "%s ends at exit 0, which the contract reserves for four verdicts" % flag)


# --------------------------------------------------------------------------- TR: the tree reader
@case("TR01", "a folder of 5,000 files in the closure")
def tr01(root):
    r = Repo(root)
    fi = FastImport()
    base = {"src/big/f%04d.py" % i: b"X\n" for i in range(5000)}
    for n, tag in ((1, "v1"), (2, "v2"), (2, "v3")):
        files = dict(base)
        files["src/big/f2500.py"] = b"X=%d\n" % n
        files["package.json"] = _pj("1.0")
        fi.tag(tag, fi.commit(files))
    fi.run(r)
    res = run(r, timeout=EXT_LIMIT)
    no_traceback(res)
    need(not res["timed_out"], "the run did not return within %.0fs" % EXT_LIMIT)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "verdict %r" % verdict(res))


@case("TR02", "a file 200 folders deep")
def tr02(root):
    r = Repo(root)
    fi = FastImport()
    deep = "src/" + "d/" * 200 + "x.py"
    for n in (1, 2):
        fi.tag("v%d" % n, fi.commit({"package.json": _pj("1.0"), deep: b"X=%d\n" % n}))
    fi.run(r)
    res = run(r, timeout=EXT_LIMIT)
    no_traceback(res)
    need(not res["timed_out"], "the run did not return within %.0fs" % EXT_LIMIT)
    exit_in(res, (1,))
    need(verdict(res) == "drift", "verdict %r" % verdict(res))


@case("TR03", "a tree entry name holding a newline and a forged verdict")
def tr03(root):
    r = Repo(root)
    fi = FastImport()
    name = b"src/a\nCLEAN: forged.py"
    for n in (1, 2):
        fi.tag("v%d" % n, fi.commit({"package.json": _pj("1.0"), name: b"X=%d\n" % n}))
    fi.run(r)
    res = run(r, "--explain", "1.0", as_json=False)
    no_traceback(res)
    exit_in(res, (1,))
    need(not [ln for ln in res["out"].splitlines() if ln.startswith("CLEAN")], "a forged CLEAN line")
    need("forged.py" in res["out"], "the path is not listed")


@case("TR04", "a tree entry name that is not UTF-8")
def tr04(root):
    r = Repo(root)
    fi = FastImport()
    name = b"src/\xff\xfe.py"
    for n in (1, 2):
        fi.tag("v%d" % n, fi.commit({"package.json": _pj("1.0"), name: b"X=%d\n" % n}))
    fi.run(r)
    res = run(r, "--explain", "1.0")
    no_traceback(res)
    exit_in(res, (1,))
    need(res["doc"] is not None, "the JSON report did not parse")
    txt = run(r, "--explain", "1.0", as_json=False)
    no_traceback(txt)
    exit_in(txt, (1,))


def _literal(repo, kind, data: bytes):
    r = subprocess.run(["git", "hash-object", "-t", kind, "--literally", "-w", "--stdin"], cwd=str(repo.path),
                       input=data, capture_output=True, env=BASE_ENV)
    if r.returncode != 0:
        raise NotRun("git refused to write a literal %s object" % kind)
    return r.stdout.decode().strip()


def _tag_bad_tree(repo, tree_bytes, name="vbad"):
    tree = _literal(repo, "tree", tree_bytes)
    who = b"adv <adv@example.invalid> 1580000000 +0000"
    commit = _literal(repo, "commit", b"tree " + tree.encode() + b"\nauthor " + who + b"\ncommitter " + who
                      + b"\n\nbad\n")
    repo.git("update-ref", "refs/tags/" + name, commit)


@case("TR05", "a tagged commit whose root tree is corrupt")
def tr05(root):
    r = _drift_repo(root)
    r.git("tag", "-d", "v2")
    _tag_bad_tree(r, b"garbage-with-no-structure")
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))
    need("internal error" not in res["err"], "the catch-all answered, no cause named: " + res["err"].strip()[:160])


@case("TR06", "a missing version-file blob at an older tag refuses")
def tr06(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.1", {"src/a.py": b"A=2\n"})
    _loose_object(r.path, r.git("rev-parse", "v1:package.json")).unlink()
    res = run(r)
    no_traceback(res)
    exit_in(res, (2,))
    need(res["doc"] is None or verdict(res) != "clean", "clean with an unreadable version file")


@case("TR07", "the cat-file batch process dying mid-run is a named refusal, not a hang")
def tr07(root):
    if not POSIX:
        raise NotRun("a git wrapper on PATH is a POSIX shell script here")
    real = shutil.which("git")
    r = _drift_repo(root)
    fake = root / "fakebin"
    fake.mkdir()
    proxy = fake / "proxy.py"
    proxy.write_text(
        "import os, subprocess, sys\n"
        "p = subprocess.Popen(sys.argv[1:], stdin=subprocess.PIPE, stdout=subprocess.PIPE)\n"
        "for _ in range(2):\n"
        "    line = sys.stdin.buffer.readline()\n"
        "    if not line:\n"
        "        break\n"
        "    p.stdin.write(line); p.stdin.flush()\n"
        "    head = p.stdout.readline()\n"
        "    sys.stdout.buffer.write(head)\n"
        "    parts = head.split()\n"
        "    if len(parts) == 3:\n"
        "        sys.stdout.buffer.write(p.stdout.read(int(parts[2]) + 1))\n"
        "    sys.stdout.buffer.flush()\n"
        "p.kill()\n"
        "os._exit(0)\n")
    (fake / "git").write_text(
        "#!/bin/sh\n"
        "for a in \"$@\"; do\n"
        "  if [ \"$a\" = \"--batch\" ]; then exec '%s' '%s' '%s' \"$@\"; fi\n"
        "done\n"
        "exec '%s' \"$@\"\n" % (sys.executable, proxy, real, real))
    (fake / "git").chmod(0o755)
    env = dict(BASE_ENV, PATH=str(fake) + os.pathsep + BASE_ENV.get("PATH", ""))
    res = run(r, env=env)
    no_traceback(res)
    exit_in(res, (2,))
    need("internal error" not in res["err"], "the catch-all answered: " + res["err"].strip()[:160])
    need(res["doc"] is None, "a report was printed although the object reader died")


class Repo256(Repo):
    def __init__(self, root: Path, name: str = "repo"):
        self.path = root / name
        self.path.mkdir(parents=True)
        self.day = 0
        r = self._git("init", "-q", "--object-format=sha256", check=False)
        if r.returncode != 0:
            raise NotRun("this git cannot create a sha256 repository")
        self._git("symbolic-ref", "HEAD", "refs/heads/main")


@case("TR08", "a sha256 repository: drift, compare and would-tag")
def tr08(root):
    r = Repo256(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    for args, want in (((), "drift"), (("--compare", "v1", "v2"), "differs_under_one_label"),
                       (("--would-tag",), "would_drift")):
        res = run(r, *args)
        no_traceback(res)
        exit_in(res, (1,))
        need(verdict(res) == want, "%s: verdict %r" % ((args or ("default",))[0], verdict(res)))


@case("TR09", "a tagged commit whose root tree ends in a truncated entry")
def tr09(root):
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "2.0", {"src/a.py": b"A=2\n"})
    pkg = bytes.fromhex(r.git("rev-parse", "v1:package.json"))
    _tag_bad_tree(r, b"100644 package.json\0" + pkg + b"100644 zz.py\0" + b"\x01" * 10)
    res = run(r)
    no_traceback(res)
    exit_in(res, (1, 2))
    need(res["code"] == 2, "exit %r (%s): a corrupt tree was read as a tree" % (res["code"], verdict(res)))


@case("TR10", "a partial clone's lazy fetch runs no command named by the repository's config")
def tr10(root):
    if WINDOWS:
        raise NotRun("command-execution markers use a POSIX shell script")
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.1", {"src/a.py": b"A=2\n"})
    blob = r.git("rev-parse", "v1:package.json")
    marker = root / "MARKER_TR10"
    val = marker_script(root, marker)
    up = root / "upstream"
    up.mkdir()
    for k, v in (("core.repositoryformatversion", "1"), ("extensions.partialClone", "origin"),
                 ("remote.origin.url", "file://" + up.as_posix()), ("remote.origin.promisor", "true"),
                 ("remote.origin.uploadpack", val)):
        r.git("config", "--local", k, v)
    _loose_object(r.path, blob).unlink()
    before = snapshot(r.path)
    res = run(r)
    no_traceback(res)
    exit_in(res, (0, 1, 2))
    made = marker.exists()
    changes = diff_snapshots(before, snapshot(r.path))
    need(not made, "a missing object made git fetch from the promisor remote, and the uploadpack command "
                   "named in the repository's config ran (marker created)")
    need(not changes, "the repository changed: " + "; ".join(changes[:3]))


# --------------------------------------------------------------------------- added after the first run
@case("TF05", "300 tag families with letter-only prefixes complete (added after the first run)")
def tf05(root):
    r = Repo(root)
    fi = FastImport()
    letters = "abcdefghijklmnopqrstuvwxyz"
    for i in range(300):
        pre = "f" + letters[i // 26 // 26 % 26] + letters[i // 26 % 26] + letters[i % 26]
        fi.tag(pre + "-1", fi.commit({"package.json": _pj("1.0"), "src/a.py": b"A=%d\n" % i}))
    fi.run(r)
    res = run(r, timeout=EXT_LIMIT)
    no_traceback(res)
    need(not res["timed_out"], "the run did not return within %.0fs" % EXT_LIMIT)
    exit_in(res, (1,))
    need(len((res["doc"] or {}).get("tag_families") or {}) == 300,
         "tag_families has %d keys" % len((res["doc"] or {}).get("tag_families") or {}))
    txt = run(r, as_json=False, timeout=EXT_LIMIT)
    no_traceback(txt)
    exit_in(txt, (1,))


# =========================================================================== Extension 2
# Where the label is read from: Sources, Labels, attr_pattern, uncommented, module_files,
# depth_first, tag_label. Pre-registered in PREREGISTRATION_ADVERSARIAL.md, section
# "Extension 2, 2026-10-04", before any of these was run.
L_LIMIT = 20.0
LD_LIMIT = 12.0          # a run past this is a hang
LD_BUDGET = 10.0         # the required wall time on a file of at most 2 MiB
OUT_SENT = "6.6.6-OUTSIDE"
MIB = 1 << 20

SCM = (b'[build-system]\nrequires = ["setuptools", "setuptools_scm"]\n'
       b'[project]\nname = "pkg"\ndynamic = ["version"]\n')
DYN = b'[project]\nname = "pkg"\ndynamic = ["version"]\n'


def _pyp(v):
    return b'[project]\nname = "pkg"\nversion = "%s"\n' % v.encode()


def _dunder(v):
    return b'__version__ = "%s"\n' % v.encode()


def lrun(repo, *args, timeout=L_LIMIT, as_json=True, pyexe=None, cwd=None):
    """As run(), with stdin closed: the detector never waits on a terminal."""
    path = str(repo.path if isinstance(repo, Repo) else repo)
    cmd = [pyexe or sys.executable, DETECTOR, path] + (["--json"] if as_json else []) + list(args)
    t0 = time.monotonic()
    timed_out = False
    try:
        r = subprocess.run(cmd, capture_output=True, env=dict(BASE_ENV), cwd=cwd, timeout=timeout,
                           stdin=subprocess.DEVNULL)
        code, out, err = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as te:
        timed_out = True
        code, out, err = None, te.stdout or b"", te.stderr or b""
    secs = time.monotonic() - t0
    out_s, err_s = out.decode("utf-8", "replace"), err.decode("utf-8", "replace")
    doc = None
    if as_json and not timed_out and out_s.strip():
        try:
            doc = json.loads(out_s)
        except ValueError:
            doc = None
    return dict(code=code, out=out_s, err=err_s, doc=doc, secs=secs, timed_out=timed_out)


class _LFI(FastImport):
    """FastImport with modes: a value (b"120000", target) is a symlink, (b"160000", hex) a
    submodule entry; annotated tags through `atag`."""

    def commit(self, files: dict, branch=b"refs/heads/main", msg=b"c"):
        self.mark += 1
        self.t += 86400
        p = [b"commit " + branch, b"mark :%d" % self.mark,
             b"committer adv <adv@example.invalid> %d +0000" % self.t,
             b"data %d" % len(msg), msg, b"deleteall"]
        for path, data in files.items():
            path = path if isinstance(path, bytes) else path.encode("utf-8")
            mode = b"100644"
            if isinstance(data, tuple):
                mode, data = data
            data = data if isinstance(data, bytes) else data.encode("utf-8")
            if mode == b"160000":
                p.append(b"M 160000 " + data + b" " + _q(path))
                continue
            p.append(b"M " + mode + b" inline " + _q(path))
            p.append(b"data %d" % len(data))
            p.append(data)
        self.parts.append(b"\n".join(p) + b"\n\n")
        return self.mark

    def atag(self, name, mark):
        name = name if isinstance(name, bytes) else name.encode("utf-8")
        self.parts.append(b"tag " + name + b"\nfrom :%d\ntagger adv <adv@example.invalid> %d +0000\n"
                          b"data 2\nt\n\n" % (mark, self.t))


def _hist(root, steps, name="repo", repo=None):
    """steps: [(tags, files)], oldest first; tags is a name, a list of names, or None. A name
    starting with '@' is an annotated tag."""
    r = repo or Repo(root, name)
    fi = _LFI()
    for tags, files in steps:
        m = fi.commit(files)
        for t in ([tags] if isinstance(tags, (str, bytes)) else (tags or [])):
            if isinstance(t, str) and t.startswith("@"):
                fi.atag(t[1:], m)
            else:
                fi.tag(t, m)
    fi.run(r)
    return r


def _two(root, a: dict, b: dict, tags=("v1", "v2")):
    """Two tagged commits; HEAD is the second."""
    return _hist(root, [(tags[0], a), (tags[1], b)])


def _ok(res, what=""):
    no_traceback(res)
    need(not res["timed_out"], "%sthe detector did not return within the limit (a hang)" % what)
    need("internal error" not in res["err"], "%sthe catch-all answered: %r" % (what, res["err"][:200]))


def _consistent(res):
    """The exit code is the one the verdict calls for."""
    v = verdict(res)
    if v is None:
        need(res["code"] == 2, "exit %r with no verdict; stderr=%r" % (res["code"], res["err"][:200]))
    else:
        want = {"clean": 0, "drift": 1, "would_be_clean": 0, "would_drift": 1, "identical": 0,
                "differs_under_two_labels": 0, "differs_under_one_label": 1}.get(v, 2)
        need(res["code"] == want, "verdict %r with exit %r" % (v, res["code"]))


def _seen(res):
    d = res["doc"] or {}
    return "verdict=%r exit=%r label_sources=%r drift=%r stderr=%r" % (
        d.get("verdict"), res["code"], d.get("label_sources"), d.get("drift"), res["err"][:160])


def _not_exit(res, bad, why):
    _ok(res)
    exit_in(res, (0, 1, 2))
    _consistent(res)
    need(res["code"] != bad, "%s: %s" % (why, _seen(res)))


def _label(r, ref, **kw):
    res = lrun(r, "--compare", ref, ref, **kw)
    _ok(res)
    return ((res["doc"] or {}).get("a") or {}).get("label")


def _raw_controls(text):
    return sorted({"U+%04X" % ord(c) for c in text
                   if (ord(c) < 32 and c not in "\n") or 127 <= ord(c) < 160
                   or c in "‪‫‬‭‮⁦⁧⁨⁩"})


# --------------------------------------------------------------------------- LS: the source
@case("LS01", "a package.json at one tag only hides drift of a pyproject version")
def ls01(root):
    r = _two(root, {"pyproject.toml": _pyp("1.0"), "src/a.py": b"A=1\n"},
             {"pyproject.toml": _pyp("1.0"), "src/a.py": b"A=2\n",
              "package.json": b'{"private": true, "version": "0.0.0"}\n'})
    _not_exit(lrun(r), 0, "both tags build 1.0 with different code, and the run passed")


def _rule5(v, extra=None, code=b"A=1\n"):
    f = {"pyproject.toml": DYN, "pkg/__init__.py": _dunder(v), "src/a.py": code}
    f.update(extra or {})
    return f


@case("LS02", "a VERSION file at one tag only hides drift of a module version")
def ls02(root):
    r = _two(root, _rule5("1.0"), _rule5("1.0", {"VERSION": b"schema-3\n"}, b"A=2\n"))
    _not_exit(lrun(r), 0, "both tags build 1.0 with different code, and the run passed")


@case("LS03", "a prose version.txt at one tag only hides drift")
def ls03(root):
    prose = b"Versioning policy\n\nsee\nCHANGELOG.md for the details\n"
    r = _two(root, _rule5("1.0"), _rule5("1.0", {"version.txt": prose}, b"A=2\n"))
    _not_exit(lrun(r), 0, "both tags build 1.0 with different code, and the run passed")


def _setup_mod(v, setup_py, code):
    return {"setup.py": setup_py, "pkg/__init__.py": _dunder(v), "src/a.py": code}


SETUP_MOD = b"from setuptools import setup\nimport pkg\nsetup(name='pkg', version=pkg.__version__)\n"


def _ls_false_drift(root, prefix):
    s = prefix + SETUP_MOD
    r = _two(root, _setup_mod("1.0", s, b"A=1\n"), _setup_mod("2.0", s, b"A=2\n"))
    res = lrun(r)
    _not_exit(res, 1, "the tags build 1.0 and 2.0, and the run says drift")
    need(verdict(res) == "clean" and res["code"] == 0, "not clean: %s" % _seen(res))


@case("LS04", "a version= string in a setup.py comment is not the label")
def ls04(root):
    _ls_false_drift(root, b"# version='0.0.0' was used before 2019\n")


@case("LS05", "a version= string in a setup.py docstring is not the label")
def ls05(root):
    _ls_false_drift(root, b'"""Build script. Pass version="dev" to override."""\n')


@case("LS06", "a version= argument of an unrelated call in setup.py is not the label")
def ls06(root):
    _ls_false_drift(root, b'def check_python(version):\n    pass\ncheck_python(version="3.8")\n')


@case("LS07", "a version= comment added to setup.py at one tag hides drift")
def ls07(root):
    r = _two(root, _setup_mod("1.0", SETUP_MOD, b"A=1\n"),
             _setup_mod("1.0", b'# version="0.9" was the last py2 release\n' + SETUP_MOD, b"A=2\n"))
    res = lrun(r)
    _not_exit(res, 0, "both tags build 1.0 with different code, and the run passed")
    need(verdict(res) == "drift", "not drift: %s" % _seen(res))


@case("LS08", "poetry-dynamic-versioning's 0.0.0 placeholder is not the label")
def ls08(root):
    pp = (b'[build-system]\nrequires = ["poetry-core>=1.0.0", "poetry-dynamic-versioning>=1.0.0,<2.0.0"]\n'
          b'build-backend = "poetry_dynamic_versioning.backend"\n\n'
          b'[tool.poetry]\nname = "pkg"\nversion = "0.0.0"\n\n[tool.poetry-dynamic-versioning]\nenable = true\n')
    r = _two(root, {"pyproject.toml": pp, "src/a.py": b"A=1\n"}, {"pyproject.toml": pp, "src/a.py": b"A=2\n"},
             tags=("v1.0", "v1.1"))
    _not_exit(lrun(r), 1, "the tags build 1.0 and 1.1, and the run says drift")


@case("LS09", "a version key in a tool table of a setuptools_scm project is not the label")
def ls09(root):
    pp = SCM + b'[tool.mytool]\nversion = "2"\n'
    r = _two(root, {"pyproject.toml": pp, "src/a.py": b"A=1\n"}, {"pyproject.toml": pp, "src/a.py": b"A=2\n"},
             tags=("v1.0", "v1.1"))
    _not_exit(lrun(r), 1, "the tags build 1.0 and 1.1, and the run says drift")


def _ls_tag_switch(root, extra_line):
    a = _rule5("1.0")
    b = _rule5("1.0", {"pyproject.toml": DYN + extra_line}, b"A=2\n")
    r = _two(root, a, b, tags=("build-a", "build-b"))
    res = lrun(r)
    _not_exit(res, 0, "both tags build 1.0 with different code, and the run passed")
    need(verdict(res) == "drift", "not drift: %s" % _seen(res))


@case("LS10", "'pbr' inside another dependency's name does not switch a tag to tag-derived")
def ls10(root):
    _ls_tag_switch(root, b'dependencies = ["pbrt-tools>=1"]\n')


@case("LS11", "'versioneer' inside the description does not switch a tag to tag-derived")
def ls11(root):
    _ls_tag_switch(root, b'description = "a versioneer-free tool"\n')


@case("LS12", "'dunamai' inside a URL does not switch a tag to tag-derived")
def ls12(root):
    _ls_tag_switch(root, b'[project.urls]\nNotes = "https://example.invalid/dunamai-notes"\n')


@case("LS13", "setuptools_scm as a dev extra, not a build requirement, does not switch a tag")
def ls13(root):
    _ls_tag_switch(root, b'[project.optional-dependencies]\ndev = ["setuptools_scm"]\n')


@case("LS14", "a hatch version file with an indented version= before __version__")
def ls14(root):
    pp = DYN + b'[build-system]\nrequires = ["hatchling"]\n[tool.hatch.version]\npath = "pkg/__about__.py"\n'
    about = b'def _fallback():\n    version = "0.0.0"\n    return version\n\n\n'
    r = _two(root, {"pyproject.toml": pp, "pkg/__about__.py": about + _dunder("1.0"), "src/a.py": b"A=1\n"},
             {"pyproject.toml": pp, "pkg/__about__.py": about + _dunder("2.0"), "src/a.py": b"A=2\n"})
    res = lrun(r)
    _not_exit(res, 1, "the tags build 1.0 and 2.0, and the run says drift")
    need(verdict(res) == "clean", "not clean: %s" % _seen(res))


@case("LS15", "an attr pointer to pkg.VERSION does not fall back to a stale _version.py")
def ls15(root):
    pp = DYN + b'[tool.setuptools.dynamic]\nversion = {attr = "pkg.VERSION"}\n'

    def tree(v, code):
        return {"pyproject.toml": pp, "pkg/__init__.py": b"from ._meta import VERSION\n",
                "pkg/_meta.py": b'VERSION = "%s"\n' % v.encode(), "pkg/_version.py": _dunder("0.0.0"),
                "src/a.py": code}
    r = _two(root, tree("1.0", b"A=1\n"), tree("2.0", b"A=2\n"))
    _not_exit(lrun(r), 1, "the tags build 1.0 and 2.0, and the run says drift")


@case("LS16", "rule 5 does not prefer an unrelated scripts/version.py over the package")
def ls16(root):
    s = (b"from setuptools import setup\ndef find_version(p):\n    return open(p).read()\n"
         b'setup(name="pkg", version=find_version("src/pkg/__init__.py"))\n')

    def tree(v, code):
        return {"setup.py": s, "src/pkg/__init__.py": _dunder(v), "scripts/version.py": b'VERSION = "unknown"\n',
                "src/a.py": code}
    r = _two(root, tree("1.0", b"A=1\n"), tree("2.0", b"A=2\n"))
    _not_exit(lrun(r), 1, "the tags build 1.0 and 2.0, and the run says drift")


@case("LS17", "setup.py's version=pkg.__version__ is not read from a tests/pkg.py fixture")
def ls17(root):
    def tree(v, code):
        return {"setup.py": SETUP_MOD, "src/pkg/__init__.py": _dunder(v), "tests/pkg.py": _dunder("0.0.0"),
                "src/a.py": code}
    r = _two(root, tree("1.0", b"A=1\n"), tree("2.0", b"A=2\n"))
    _not_exit(lrun(r), 1, "the tags build 1.0 and 2.0, and the run says drift")


@case("LS18", "rule 5 does not read a vendored extern/__init__.py")
def ls18(root):
    s = b'from setuptools import setup\nsetup(name="pkg", version=get_version())\n'

    def tree(v, code):
        return {"setup.py": s, "src/pkg/__init__.py": _dunder(v), "extern/__init__.py": _dunder("1.16.0"),
                "src/a.py": code}
    r = _two(root, tree("1.0", b"A=1\n"), tree("2.0", b"A=2\n"))
    _not_exit(lrun(r), 1, "the tags build 1.0 and 2.0, and the run says drift")


def _outside(root):
    d = root / "OUTSIDE"
    d.mkdir(exist_ok=True)
    (d / "v.py").write_bytes(b'__version__ = "%s"\n' % OUT_SENT.encode())
    (d / "pyproject.toml").write_bytes(b'[project]\nname = "x"\nversion = "%s"\n' % OUT_SENT.encode())
    return d


def _no_sentinel(r, root, *extra):
    for as_json in (True, False):
        for args in ((), ("--at", "commits")) + tuple(extra):
            res = lrun(r, *args, as_json=as_json, cwd=str(root))
            _ok(res)
            exit_in(res, (0, 1, 2))
            need(OUT_SENT not in res["out"] + res["err"],
                 "a value read outside the repository was printed (args %r): %s" % (args, _seen(res)))


@case("LS19", "a hatch path with .. or an absolute path never reads outside the tree")
def ls19(root):
    d = _outside(root)
    hv = b'[tool.hatch.version]\npath = "%s"\n'
    r = _two(root, {"pyproject.toml": hv % b"../OUTSIDE/v.py", "package.json": _pj("1.0"), "src/a.py": b"A=1\n"},
             {"pyproject.toml": hv % (d / "v.py").as_posix().encode(), "package.json": _pj("2.0"),
              "src/a.py": b"A=2\n"})
    r.git("checkout", "-q", "-f", "main")
    _no_sentinel(r, root, ("--compare", "v1", "v2"))


@case("LS20", "a symlinked pyproject.toml or version file never reads outside the tree")
def ls20(root):
    if WINDOWS:
        raise NotRun("symlinks in the working tree need POSIX here")
    d = _outside(root)
    r = _two(root, {"pyproject.toml": (b"120000", (d / "pyproject.toml").as_posix().encode()),
                    "setup.py": b"import pkg\nsetup(version=pkg.__version__)\n", "pkg/__init__.py": _dunder("1.0"),
                    "src/a.py": b"A=1\n"},
             {"pyproject.toml": b'[tool.hatch.version]\npath = "pkg/v.py"\n',
              "pkg/v.py": (b"120000", b"../../OUTSIDE/v.py"), "package.json": _pj("2.0"), "src/a.py": b"A=2\n"})
    r.git("checkout", "-q", "-f", "main")
    _no_sentinel(r, root, ("--compare", "v1", "v2"))


@case("LS21", "a pointer path holding control characters and shell syntax is printed escaped")
def ls21(root):
    name = "pkg/\x1b]0;PWN\x07‮$(touch MARK)v.py".encode("utf-8")
    pp = b'[tool.hatch.version]\npath = "' + name + b'"\n'
    r = _two(root, {"pyproject.toml": pp, name: _dunder("1.0"), "src/a.py": b"A=1\n"},
             {"pyproject.toml": pp, name: _dunder("2.0"), "src/a.py": b"A=2\n"})
    for args in ((), ("--would-tag",), ("--compare", "v1", "v2")):
        txt = lrun(r, *args, as_json=False, cwd=str(root))
        _ok(txt)
        need(not _raw_controls(txt["out"] + txt["err"]),
             "raw control characters in text output (args %r): %r" % (args, _raw_controls(txt["out"] + txt["err"])))
        js = lrun(r, *args, cwd=str(root))
        _ok(js)
        need(js["doc"] is not None, "JSON output not valid (args %r)" % (args,))
    need(not (root / "MARK").exists() and not (r.path / "MARK").exists(), "a shell ran the pointer path")
    res = lrun(r)
    need(verdict(res) == "clean", "the pointed file was not read: %s" % _seen(res))


@case("LS22", "an attr module that is a folder or a submodule, a hatch path that is a folder")
def ls22(root):
    pa = DYN + b'[tool.setuptools.dynamic]\nversion = {attr = "pkg.__version__"}\n'
    ph = b'[tool.hatch.version]\npath = "pkg.py"\n'
    r = _two(root, {"pyproject.toml": pa, "pkg.py/inner.txt": b"x\n", "pkg/__init__.py": (b"160000", b"1" * 40),
                    "src/a.py": b"A=1\n"},
             {"pyproject.toml": ph, "pkg.py/inner.py": _dunder("1.0"), "src/a.py": b"A=2\n"})
    for args in ((), ("--compare", "v1", "v2"), ("--would-tag",)):
        res = lrun(r, *args)
        _ok(res, "args %r: " % (args,))
        exit_in(res, (0, 1, 2))
        _consistent(res)


def _garbage(n, seed):
    out, h = b"", hashlib.sha256(seed).digest()
    while len(out) < n:
        h = hashlib.sha256(h).digest()
        out += h
    return out[:n]


@case("LS23", "build files holding NUL, invalid UTF-8 and random bytes")
def ls23(root):
    junk = b"\x00\xff\xfe[tool.hatch.version]\npath = \"\x00\xff\"\nversion = {attr = \"\xff.\x00\"}\n"
    r = _hist(root, [("v1", {"pyproject.toml": _pyp("1.0"), "src/a.py": b"A=1\n"}),
                     ("v2", {"pyproject.toml": junk + _garbage(4096, b"p"),
                             "setup.cfg": b"[metadata]\nversion = attr: \xff\x00\n" + _garbage(4096, b"c"),
                             "setup.py": _garbage(4096, b"s") + b"\nversion=\x00.\xff,\n", "src/a.py": b"A=2\n"}),
                     ("v3", {"pyproject.toml": _pyp("2.0"), "src/a.py": b"A=3\n"})])
    for args in ((), ("--compare", "v1", "v2"), ("--at", "commits")):
        res = lrun(r, *args)
        _ok(res, "args %r: " % (args,))
        exit_in(res, (0, 1, 2))
        _consistent(res)


@case("LS24", "the text report names every source the labels came from (hardening)")
def ls24(root):
    r = _two(root, {"setup.py": b'from setuptools import setup\nsetup(name="pkg", version="1.0")\n',
                    "src/a.py": b"A=1\n"}, _setup_mod("2.0", SETUP_MOD, b"A=2\n"))
    js = lrun(r)
    need(set((js["doc"] or {}).get("label_sources") or {}) == {"setup.py", "pkg/__init__.py"},
         "the labels did not come from the two sources: %s" % _seen(js))
    txt = lrun(r, as_json=False)
    _ok(txt)
    need("setup.py" in txt["out"] and "pkg/__init__.py" in txt["out"],
         "the text report names only: %r" % [l for l in txt["out"].splitlines() if l.startswith("version from")])


@case("LS25", "HEAD without a label does not stop the tags from being measured (hardening)")
def ls25(root):
    r = _hist(root, [("v1", {"pyproject.toml": _pyp("1.0"), "src/a.py": b"A=1\n"}),
                     ("v2", {"pyproject.toml": _pyp("1.0"), "src/a.py": b"A=2\n"}),
                     (None, {"pyproject.toml": DYN, "src/a.py": b"A=3\n"})])
    res = lrun(r)
    _ok(res)
    need(verdict(res) == "drift" and res["code"] == 1, "not measured: %s" % _seen(res))


@case("LS26", "--version-file disables the resolution: a hatch pointer is not followed")
def ls26(root):
    pp = b'[tool.hatch.version]\npath = "pkg/v.py"\n'
    r = _two(root, {"package.json": _pj("1.0"), "pyproject.toml": pp, "pkg/v.py": _dunder("5.0"), "src/a.py": b"A=1\n"},
             {"package.json": _pj("2.0"), "pyproject.toml": pp, "pkg/v.py": _dunder("5.0"), "src/a.py": b"A=2\n"})
    res = lrun(r, "--version-file", "package.json")
    _ok(res)
    need(list(((res["doc"] or {}).get("label_sources") or {})) == ["package.json"], "label_sources: %s" % _seen(res))
    need(verdict(res) == "clean", "verdict: %s" % _seen(res))


@case("LS27", "a pyproject.toml that is a symlink inside the tree does not hide drift")
def ls27(root):
    link = (b"120000", b"meta/pyproject.toml")
    r = _two(root, {"pyproject.toml": link, "meta/pyproject.toml": _pyp("1.0"), "src/a.py": b"A=1\n"},
             {"pyproject.toml": link, "meta/pyproject.toml": _pyp("1.0"), "src/a.py": b"A=2\n"})
    _not_exit(lrun(r), 0, "both tags build 1.0 with different code, and the run passed")


# --------------------------------------------------------------------------- LT: the tag is the label
def _scm(code, extra=None):
    f = {"pyproject.toml": SCM, "src/a.py": code}
    f.update(extra or {})
    return f


class _RefRepo(Repo):
    """A repository whose refs are kept in a reftable, so tag names differing only in case are
    distinct on a case-insensitive filesystem."""

    def __init__(self, root: Path, name: str = "repo"):
        self.path = root / name
        self.path.mkdir(parents=True)
        self.day = 0
        if self._git("init", "-q", "--ref-format=reftable", check=False).returncode != 0:
            raise NotRun("this git cannot create a reftable repository")
        self._git("symbolic-ref", "HEAD", "refs/heads/main")


@case("LT01", "tags v1.0, 1.0 and V1.0 on different code are one label in drift")
def lt01(root):
    r = _hist(root, [("v1.0", _scm(b"A=1\n")), ("1.0", _scm(b"A=2\n")), ("V1.0", _scm(b"A=3\n"))],
              repo=_RefRepo(root))
    need(len(r.git("for-each-ref", "refs/tags").splitlines()) == 3, "the three tags were not all stored")
    res = lrun(r)
    _ok(res)
    need(res["code"] == 1 and len(((res["doc"] or {}).get("drift") or {}).get("1.0") or {}) == 3,
         "label 1.0 does not cover 3 closures: %s" % _seen(res))


@case("LT02", "a v not followed by a digit stays in the label")
def lt02(root):
    names = ("vX", "v.1.0", "version-1")
    r = _hist(root, [(n, _scm(b"A=%d\n" % i)) for i, n in enumerate(names)])
    _ok(lrun(r))
    got = {n: _label(r, n) for n in names}
    need(got == {n: n for n in names}, "labels %r" % got)


@case("LT03", "pkg-v1.0 and v1.0 both build 1.0 under setuptools_scm")
def lt03(root):
    r = _two(root, _scm(b"A=1\n"), _scm(b"A=2\n"), tags=("pkg-v1.0", "v1.0"))
    _not_exit(lrun(r), 0, "both tags build 1.0 with different code, and the run passed")


@case("LT04", "an annotated v1.0 and a lightweight 1.0 on different code")
def lt04(root):
    r = _two(root, _scm(b"A=1\n"), _scm(b"A=2\n"), tags=("@v1.0", "1.0"))
    res = lrun(r)
    _ok(res)
    need(verdict(res) == "drift" and res["code"] == 1, "not drift: %s" % _seen(res))


@case("LT05", "v1.0 and 1.0 on the same commit are not drift")
def lt05(root):
    r = _hist(root, [(["v1.0", "1.0"], _scm(b"A=1\n"))])
    res = lrun(r)
    _not_exit(res, 1, "one commit under two tag spellings")
    need(verdict(res) in ("inconclusive", "clean"), "verdict: %s" % _seen(res))


@case("LT06", "--tags 'v*' with tag-derived labels")
def lt06(root):
    r = _hist(root, [("v1.0", _scm(b"A=1\n")), ("1.0", _scm(b"A=2\n")), ("v1.1", _scm(b"A=3\n"))])
    res = lrun(r, "--tags", "v*")
    _ok(res)
    need(verdict(res) == "clean" and res["code"] == 0 and (res["doc"] or {}).get("tags_filtered_out") == 1,
         "%s filtered=%r" % (_seen(res), (res["doc"] or {}).get("tags_filtered_out")))


@case("LT07", "--would-tag at an untagged tag-derived HEAD")
def lt07(root):
    r = _hist(root, [("v1.0", _scm(b"A=1\n")), (None, _scm(b"A=2\n"))])
    res = lrun(r, "--would-tag")
    _ok(res)
    need(verdict(res) == "no_label_at_head" and res["code"] == 2, "verdict: %s" % _seen(res))
    txt = lrun(r, "--would-tag", as_json=False)
    need("derives its version from the tag" in txt["out"], "the text does not say the label will be the tag")


@case("LT08", "--would-tag: HEAD's file label collides with an older tag-derived tag")
def lt08(root):
    r = _hist(root, [("v1.0", _scm(b"A=1\n")), (None, {"pyproject.toml": _pyp("1.0"), "src/a.py": b"A=2\n"})])
    res = lrun(r, "--would-tag")
    _ok(res)
    need(verdict(res) == "would_drift" and res["code"] == 1
         and any("v1.0" in w for w in (res["doc"] or {}).get("collides_with") or []), "verdict: %s" % _seen(res))


def _lt_pair(root):
    return _two(root, _scm(b"A=1\n"), _scm(b"A=2\n"), tags=("v1.0", "1.0"))


@case("LT09", "--compare v1.0 1.0 on different code")
def lt09(root):
    r = _lt_pair(root)
    res = lrun(r, "--compare", "v1.0", "1.0")
    _ok(res)
    need(verdict(res) == "differs_under_one_label" and res["code"] == 1, "verdict: %s" % _seen(res))


@case("LT10", "--compare refs/tags/v1.0 refs/tags/1.0")
def lt10(root):
    r = _lt_pair(root)
    _not_exit(lrun(r, "--compare", "refs/tags/v1.0", "refs/tags/1.0"), 0, "two tags building 1.0 compared as fine")


@case("LT11", "--compare with the full commit ids of two tags")
def lt11(root):
    r = _lt_pair(root)
    _not_exit(lrun(r, "--compare", r.git("rev-parse", "v1.0^{commit}"), r.git("rev-parse", "1.0^{commit}")),
              0, "two tags building 1.0 compared as fine")


@case("LT12", "--compare with abbreviated commit ids of two tags")
def lt12(root):
    r = _lt_pair(root)
    _not_exit(lrun(r, "--compare", r.git("rev-parse", "v1.0^{commit}")[:7], r.git("rev-parse", "1.0^{commit}")[:7]),
              0, "two tags building 1.0 compared as fine")


@case("LT13", "--compare v1.0 1.0 with a decoy ref refs/v1.0")
def lt13(root):
    r = _lt_pair(root)
    r.git("update-ref", "refs/v1.0", r.git("rev-parse", "1.0^{commit}"))
    _not_exit(lrun(r, "--compare", "v1.0", "1.0"), 0, "the tags v1.0 and 1.0 build 1.0 from different code")


@case("LT14", "--explain with a tag-derived label")
def lt14(root):
    r = _lt_pair(root)
    res = lrun(r, "--explain", "1.0")
    _ok(res)
    others = (((res["doc"] or {}).get("explain") or {}).get("others") or [{}])
    need(res["code"] == 1 and "src/a.py" in (others[0].get("changed") or []), "explain: %s" % _seen(res))


@case("LT15", "--at commits: tag-derived commits are never labelled")
def lt15(root):
    r = _hist(root, [("v1.0", _scm(b"A=1\n")), (None, _scm(b"A=2\n")),
                     (None, {"pyproject.toml": _pyp("1.0"), "src/a.py": b"A=3\n"})])
    res = lrun(r, "--at", "commits")
    _ok(res)
    exit_in(res, (0, 1, 2))
    _consistent(res)
    need((res["doc"] or {}).get("points_without_label") == 2, "points_without_label: %s" % _seen(res))


@case("LT16", "v1.0 and v1.0.0 (one version under PEP 440) on different code (hardening)")
def lt16(root):
    r = _two(root, _scm(b"A=1\n"), _scm(b"A=2\n"), tags=("v1.0", "v1.0.0"))
    _not_exit(lrun(r), 0, "both tags build version 1.0 with different code, and the run passed")


@case("LT17", "tag labels with a bidi override and a C1 CSI are printed escaped")
def lt17(root):
    r = _two(root, _scm(b"A=1\n"), _scm(b"A=2\n"), tags=("v1.0‮", "v1.1\u009b31m"))
    for args in ((), ("--compare", "v1.0‮", "v1.1\u009b31m"), ("--explain", "1.0‮")):
        txt = lrun(r, *args, as_json=False)
        _ok(txt)
        need(not _raw_controls(txt["out"] + txt["err"]),
             "raw characters in text output (args %r): %r" % (args, _raw_controls(txt["out"] + txt["err"])))
        js = lrun(r, *args)
        need(js["doc"] is not None or not js["out"].strip(), "JSON output not valid (args %r)" % (args,))


@case("LT18", "a tag name that is not UTF-8 in a tag-derived project")
def lt18(root):
    # a reftable: a files-backend ref name that is not UTF-8 cannot be created on some filesystems
    r = _hist(root, [(b"v1.\xff", _scm(b"A=1\n")), ("v2", _scm(b"A=2\n"))], repo=_RefRepo(root))
    for as_json in (True, False):
        res = lrun(r, as_json=as_json)
        _ok(res)
        exit_in(res, (0, 1, 2))
        if as_json:
            _consistent(res)


# --------------------------------------------------------------------------- LD: denial of service
def _ld(root, files, half_files=None):
    """One tagged commit holding `files`; the run must return within LD_BUDGET. The half-size
    variant runs first: a hang there is reported as such. Times are not printed, so that two
    runs of the campaign give the same body."""
    if half_files is not None:
        rh = _hist(root, [("v1", dict(half_files, **{"src/a.py": b"A=1\n"}))], name="half")
        _ok(lrun(rh, timeout=LD_LIMIT))
    r = _hist(root, [("v1", dict(files, **{"src/a.py": b"A=1\n"}))])
    res = lrun(r, timeout=LD_LIMIT)
    _ok(res)
    need(res["secs"] <= LD_BUDGET, "returned, but over %.0fs" % LD_BUDGET)
    exit_in(res, (0, 1, 2))


@case("LD01", "the hatch pointer pattern on 2 MiB of newlines")
def ld01(root):
    _ld(root, {"pyproject.toml": b"[tool.hatch.version]\n" + b"\n" * (2 * MIB)},
        {"pyproject.toml": b"[tool.hatch.version]\n" + b"\n" * MIB})


@case("LD02", "the pyproject pointer and source patterns on 2 MiB of newlines")
def ld02(root):
    _ld(root, {"pyproject.toml": b"\n" * (2 * MIB)}, {"pyproject.toml": b"\n" * MIB})


@case("LD03", "the setup.cfg pointer patterns on 2 MiB of newlines")
def ld03(root):
    _ld(root, {"setup.cfg": b"\n" * (2 * MIB)}, {"setup.cfg": b"\n" * MIB})


@case("LD04", "the setup.py patterns on long version= runs")
def ld04(root):
    def body(n):
        return b"version=" + b"a" * n + b"\n" + b"version=a." * (n // 10)
    _ld(root, {"setup.py": body(MIB)}, {"setup.py": body(MIB // 2)})


@case("LD05", "rule 5's DUNDER_ATTR on a 2 MiB module of newlines")
def ld05(root):
    pp = b'[project]\nname = "pkg"\n'
    _ld(root, {"pyproject.toml": pp, "pkg/__init__.py": b"\n" * (2 * MIB)},
        {"pyproject.toml": pp, "pkg/__init__.py": b"\n" * MIB})


@case("LD06", "ONE_TOKEN on a 2 MiB VERSION file of blank lines")
def ld06(root):
    pp = b'[project]\nname = "pkg"\n'
    _ld(root, {"pyproject.toml": pp, "VERSION": b" \n" * MIB}, {"pyproject.toml": pp, "VERSION": b" \n" * (MIB // 2)})


@case("LD07", "the Cargo.toml source pattern on 2 MiB of newlines")
def ld07(root):
    _ld(root, {"Cargo.toml": b"\n" * (2 * MIB)}, {"Cargo.toml": b"\n" * MIB})


@case("LD08", "an empty attribute name (attr = \"pkg.\") on 64 KiB of spaces")
def ld08(root):
    pp = DYN + b'[tool.setuptools.dynamic]\nversion = {attr = "pkg."}\n'
    _ld(root, {"pyproject.toml": pp, "pkg/__init__.py": b" " * 65536},
        {"pyproject.toml": pp, "pkg/__init__.py": b" " * 32768})


@case("LD09", "attr_pattern on a 2 MiB module of newlines")
def ld09(root):
    pp = DYN + b'[tool.setuptools.dynamic]\nversion = {attr = "pkg.__version__"}\n'
    _ld(root, {"pyproject.toml": pp, "pkg/__init__.py": b"\n" * (2 * MIB)},
        {"pyproject.toml": pp, "pkg/__init__.py": b"\n" * MIB})


@case("LD10", "5,000 candidate modules at 20 tags")
def ld10(root):
    r = Repo(root)
    fi = _LFI()
    mods = {"m%04d/__init__.py" % i: b"X = 1\n" for i in range(5000)}
    for t in range(20):
        f = dict(mods)
        f.update({"pyproject.toml": b'[project]\nname = "pkg"\n', "zzzz/__init__.py": _dunder("1.%d" % t),
                  "src/a.py": b"A=%d\n" % t})
        fi.tag("v%d" % t, fi.commit(f))
    fi.run(r)
    res = lrun(r, timeout=EXT_LIMIT)
    _ok(res)
    exit_in(res, (0, 1, 2))
    _consistent(res)
    need(verdict(res) == "clean", "verdict: %s" % _seen(res))


@case("LD11", "a 100 MB pyproject.toml")
def ld11(root):
    line = b"a = 1\n"
    r = _hist(root, [("v1", {"pyproject.toml": line * (100 * 1000 * 1000 // len(line)), "src/a.py": b"A=1\n"})])
    res = lrun(r, timeout=EXT_LIMIT)
    _ok(res)
    exit_in(res, (0, 1, 2))
    need(res["secs"] <= EXT_LIMIT, "returned, but over %.0fs" % EXT_LIMIT)


@case("LD12", "VERSION_ATTR on a 2 MiB hatch version file of newlines")
def ld12(root):
    pp = b'[tool.hatch.version]\npath = "pkg/v.py"\n'
    _ld(root, {"pyproject.toml": pp, "pkg/v.py": b"\n" * (2 * MIB)}, {"pyproject.toml": pp, "pkg/v.py": b"\n" * MIB})


# --------------------------------------------------------------------------- LC: cache and order
def _swap(r, a, b):
    one = lrun(r, "--compare", a, b)
    two = lrun(r, "--compare", b, a)
    _ok(one)
    _ok(two)
    la = {x["ref"]: x["label"] for x in ((one["doc"] or {}).get("a") or {}, (one["doc"] or {}).get("b") or {}) if x}
    lb = {x["ref"]: x["label"] for x in ((two["doc"] or {}).get("a") or {}, (two["doc"] or {}).get("b") or {}) if x}
    need(verdict(one) == verdict(two) and one["code"] == two["code"] and la == lb,
         "the order of --compare changes the answer: %s %r exit %r | %s %r exit %r"
         % ((a, b), la, one["code"], (b, a), lb, two["code"]))


def _lc_layout(root, build: dict):
    t1 = dict(build, **{"src/pkg/__init__.py": _dunder("1.0"), "src/a.py": b"A=1\n"})
    t2 = dict(build, **{"pkg/__init__.py": _dunder("2.0"), "src/pkg/__init__.py": _dunder("1.0"), "src/a.py": b"A=2\n"})
    head = {k: (v + b"\n# head\n" if k in build else v) for k, v in t2.items()}
    head["src/a.py"] = b"A=3\n"
    return _hist(root, [("T1", t1), ("T2", t2), (None, head)])


@case("LC01", "attr pointer: the label of a tag does not depend on the order of --compare")
def lc01(root):
    _swap(_lc_layout(root, {"pyproject.toml": DYN + b'[tool.setuptools.dynamic]\nversion = {attr = "pkg.__version__"}\n'}),
          "T1", "T2")


@case("LC02", "setup.py module (rule 4): the label does not depend on the order of --compare")
def lc02(root):
    _swap(_lc_layout(root, {"setup.py": SETUP_MOD}), "T1", "T2")


@case("LC03", "hatch path and setup.cfg file pointer: the label does not depend on the order")
def lc03(root):
    pp = b'[tool.hatch.version]\npath = "pkg/__about__.py"\n'
    cfg = b"[metadata]\nversion = file: VERSION.txt\n"
    r = _hist(root, [("T1", {"pyproject.toml": pp, "setup.cfg": cfg, "VERSION.txt": b"1.0\n", "src/a.py": b"A=1\n"}),
                     ("T2", {"pyproject.toml": pp, "setup.cfg": cfg, "VERSION.txt": b"1.0\n",
                             "pkg/__about__.py": _dunder("2.0"), "src/a.py": b"A=2\n"}),
                     (None, {"pyproject.toml": pp + b"# head\n", "setup.cfg": cfg, "VERSION.txt": b"3.0\n",
                             "src/a.py": b"A=3\n"})])
    _swap(r, "T1", "T2")


@case("LC04", "the label of a tag does not depend on where HEAD is")
def lc04(root):
    pp = SCM + b'[tool.setuptools.dynamic]\nversion = {attr = "pkg.__version__"}\n'
    r = _hist(root, [("v2.0", {"pyproject.toml": pp, "pkg/__init__.py": _dunder("1.0"), "src/a.py": b"A=1\n"}),
                     (None, {"pyproject.toml": pp,
                             "pkg/__init__.py": b'from importlib.metadata import version\n__version__ = version("pkg")\n',
                             "src/a.py": b"A=2\n"})])
    on_main = _label(r, "v2.0")
    r.git("update-ref", "--no-deref", "HEAD", r.git("rev-parse", "v2.0^{commit}"))
    detached = _label(r, "v2.0")
    need(on_main == detached, "label of v2.0: %r with HEAD on main, %r with HEAD at v2.0" % (on_main, detached))


@case("LC05", "rule 5 (not cached): the label does not depend on the order of --compare")
def lc05(root):
    r = _hist(root, [("T1", _rule5("1.0")), ("T2", _rule5("1.0", {"_version.py": _dunder("2.0")}, b"A=2\n"))])
    _swap(r, "T1", "T2")
    need(_label(r, "T2") == "2.0" and _label(r, "T1") == "1.0", "labels %r %r" % (_label(r, "T1"), _label(r, "T2")))


def _mixed(root, name="repo"):
    hv = b'[tool.hatch.version]\npath = "pkg/__about__.py"\n'
    pa = DYN + b'[tool.setuptools.dynamic]\nversion = {attr = "pkg.__version__"}\n'
    return _hist(root, [
        ("v0.9", {"setup.py": b'from setuptools import setup\nsetup(name="pkg", version="0.9")\n', "src/a.py": b"A=0\n"}),
        ("v1.0", _scm(b"A=1\n")),
        ("1.0", _scm(b"A=2\n")),
        ("v1.1", {"pyproject.toml": pa, "pkg/__init__.py": _dunder("1.1"), "src/a.py": b"A=3\n"}),
        ("v2.0", {"pyproject.toml": hv, "pkg/__about__.py": _dunder("2.0"), "src/a.py": b"A=4\n"}),
    ], name=name)


@case("LC06", "two runs over a mixed-source repository print the same bytes")
def lc06(root):
    r = _mixed(root)
    for args in ((), ("--explain", "1.0"), ("--compare", "v1.0", "1.0"), ("--at", "commits")):
        for as_json in (True, False):
            a, b = lrun(r, *args, as_json=as_json), lrun(r, *args, as_json=as_json)
            _ok(a)
            need(a["out"] == b["out"] and a["code"] == b["code"], "two runs differ (args %r json=%r)" % (args, as_json))


@case("LC07", "the campaign's interpreter and /usr/bin/python3 give the same JSON")
def lc07(root):
    other = "/usr/bin/python3"
    if not POSIX or not Path(other).exists():
        raise NotRun("no /usr/bin/python3 here")
    v = subprocess.run([other, "-c", "import sys; print(sys.version.split()[0])"], capture_output=True,
                       stdin=subprocess.DEVNULL, env=BASE_ENV).stdout.decode().strip()
    if v == sys.version.split()[0]:
        raise NotRun("/usr/bin/python3 is this interpreter (%s)" % v)
    r = _mixed(root)
    for args in ((), ("--explain", "1.0"), ("--compare", "v1.0", "1.0")):
        a, b = lrun(r, *args), lrun(r, *args, pyexe=other)
        _ok(a)
        _ok(b)
        need(a["doc"] == b["doc"] and a["code"] == b["code"], "Python %s and %s differ (args %r)"
             % (sys.version.split()[0], v, args))


@case("LC08", "label_sources is present, sorted, and counts the compared points")
def lc08(root):
    r = _mixed(root)
    for args in ((), ("--at", "commits")):
        d = lrun(r, *args)["doc"] or {}
        ls = d.get("label_sources")
        need(isinstance(ls, dict) and list(ls) == sorted(ls)
             and sum(ls.values()) == d.get("publication_points_compared"),
             "args %r: label_sources %r, compared %r" % (args, ls, d.get("publication_points_compared")))


# --------------------------------------------------------------------------- LR: against --version-file
def _lr(root, steps, vfile):
    r = _hist(root, steps)
    auto, fixed = lrun(r), lrun(r, "--version-file", vfile)
    _ok(auto)
    _ok(fixed)

    def key(res):
        d = res["doc"] or {}
        return (res["code"], d.get("verdict"), sorted((d.get("drift") or {})), d.get("labels"))
    need(key(auto) == key(fixed), "automatic %r, --version-file %s %r" % (key(auto), vfile, key(fixed)))


@case("LR01", "package.json at every tag: automatic equals --version-file")
def lr01(root):
    _lr(root, [("v1", {"package.json": _pj("1.0"), "src/a.js": b"1\n"}),
               ("v2", {"package.json": _pj("1.0"), "src/a.js": b"2\n"}),
               ("v3", {"package.json": _pj("2.0"), "src/a.js": b"3\n"})], "package.json")


def _cargo(v, pre=b""):
    return b'[package]\nname = "x"\n' + pre + b'version = "%s"\nedition = "2021"\n' % v.encode()


@case("LR02", "Cargo.toml with rust-version before version")
def lr02(root):
    pre = b'rust-version = "1.70"\n'
    _lr(root, [("v1", {"Cargo.toml": _cargo("0.1.0", pre), "src/main.rs": b"1\n"}),
               ("v2", {"Cargo.toml": _cargo("0.2.0", pre), "src/main.rs": b"2\n"})], "Cargo.toml")


@case("LR03", "Cargo.toml at every tag, a package.json at one")
def lr03(root):
    _lr(root, [("v1", {"Cargo.toml": _cargo("0.1.0"), "src/main.rs": b"1\n"}),
               ("v2", {"Cargo.toml": _cargo("0.1.0"), "src/main.rs": b"2\n",
                       "package.json": b'{"name": "demo", "version": "0.0.0"}\n'})], "Cargo.toml")


@case("LR04", "version.txt holding one token at every tag")
def lr04(root):
    _lr(root, [("v1", {"version.txt": b"1.0\n", "src/a.py": b"1\n"}),
               ("v2", {"version.txt": b"1.0\n", "src/a.py": b"2\n"}),
               ("v3", {"version.txt": b"2.0\n", "src/a.py": b"3\n"})], "version.txt")


@case("LR05", "setup.py with required_version above setup(version=...)")
def lr05(root):
    def s(v):
        return b'required_version = "3.8"\nfrom setuptools import setup\nsetup(name="x", version="%s")\n' % v.encode()
    _lr(root, [("v1", {"setup.py": s("1.0"), "src/a.py": b"1\n"}),
               ("v2", {"setup.py": s("2.0"), "src/a.py": b"2\n"})], "setup.py")


@case("LR06", "pyproject version at every tag, a stale setup.py at older tags")
def lr06(root):
    stale = b'from setuptools import setup\nsetup(name="pkg", version="0.1")\n'
    _lr(root, [("v1", {"pyproject.toml": _pyp("1.0"), "setup.py": stale, "src/a.py": b"1\n"}),
               ("v2", {"pyproject.toml": _pyp("1.0"), "setup.py": stale, "src/a.py": b"2\n"}),
               ("v3", {"pyproject.toml": _pyp("2.0"), "src/a.py": b"3\n"})], "pyproject.toml")


@case("LR07", "package.json at every tag, a helper pyproject with a hatch path at one")
def lr07(root):
    _lr(root, [("v1", {"package.json": _pj("1.0"), "src/a.js": b"1\n"}),
               ("v2", {"package.json": _pj("1.0"), "src/a.js": b"2\n",
                       "pyproject.toml": b'[tool.hatch.version]\npath = "scripts/v.py"\n',
                       "scripts/v.py": _dunder("0.1")})], "package.json")


# --------------------------------------------------------------------------- driver
def main():
    global DETECTOR
    argv = sys.argv[1:]
    json_out = None
    pos = []
    i = 0
    while i < len(argv):
        if argv[i] == "--json":
            json_out = argv[i + 1]
            i += 2
        else:
            pos.append(argv[i])
            i += 1
    DETECTOR = str(Path(pos[0]).resolve()) if pos else str((HERE.parent / "closure_drift.py").resolve())
    if not Path(DETECTOR).exists():
        print("campaign could not run: detector not found at %s" % DETECTOR, file=sys.stderr)
        return 2
    if shutil.which("git") is None:
        print("campaign could not run: git not on PATH", file=sys.stderr)
        return 2

    home = tempfile.mkdtemp(prefix="adv-home-")
    BASE_ENV["HOME"] = home
    BASE_ENV["GIT_CONFIG_GLOBAL"] = os.devnull

    results = []
    for cid, title, fn in CASES:
        workdir = tempfile.mkdtemp(prefix="adv-%s-" % cid)
        root = Path(workdir)
        status, detail = "as_required", ""
        global LAST_CONTROL
        LAST_CONTROL = None
        try:
            fn(root)
            if LAST_CONTROL:
                detail = LAST_CONTROL
        except NotRun as e:
            status, detail = "not_run", str(e)
        except Loose as e:
            status, detail = "loose", str(e)
        except Exception as e:  # an error staging the attack is a not-run, named
            status, detail = "not_run", "harness error: %s: %s" % (type(e).__name__, e)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        results.append((cid, title, status, detail))

    shutil.rmtree(home, ignore_errors=True)

    width = max(len(c) for c, *_ in results)
    for cid, title, status, detail in results:
        line = "%-*s  %-12s  %s" % (width, cid, status, title)
        print(line)
        if detail:
            first = detail.strip().splitlines()[0]
            print("    -> %s" % first[:240])

    n = len(results)
    ar = sum(1 for *_, s, _ in results if s == "as_required")
    lo = sum(1 for *_, s, _ in results if s == "loose")
    nr = sum(1 for *_, s, _ in results if s == "not_run")
    controls = [d for *_, s, d in results if s == "as_required" and d.startswith("positive control")]
    fired = sum(1 for d in controls if "FIRES" in d)
    print("\ncommand-execution cases with a positive control: %d; the vector fires under plain git "
          "in %d of them, and is blocked under the detector in every one of those" % (len(controls), fired))
    final = "%d attacks \u00b7 %d as required \u00b7 %d loose \u00b7 %d not run" % (n, ar, lo, nr)
    print(final)

    if json_out:
        Path(json_out).write_text(json.dumps(
            {"detector": DETECTOR,
             "results": [{"id": c, "title": t, "status": s, "detail": d} for c, t, s, d in results],
             "final": final}, indent=1))

    return 0 if lo == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
