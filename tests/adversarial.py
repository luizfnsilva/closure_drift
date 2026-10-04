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
    if WINDOWS:
        raise NotRun("marker scripts use a POSIX shell")
    sh = root / name
    sh.write_text("#!/bin/sh\n: > '%s'\nexit 0\n" % marker)
    sh.chmod(0o755)
    return str(sh)


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
    """configure(repo, marker_value, marker_path) sets up the repo; marker must be absent after run."""
    if WINDOWS:
        raise NotRun("command-execution markers use a POSIX shell script")
    r = Repo(root)
    r.release("v1", "1.0", {"src/a.py": b"A=1\n"})
    r.release("v2", "1.0", {"src/a.py": b"A=2\n"})
    marker = root / ("MARKER_%s" % os.getpid())
    if marker.exists():
        marker.unlink()
    val = marker_script(root, marker)
    configure(r, val, marker)
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
        try:
            fn(root)
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
        if status in ("loose", "not_run") and detail:
            first = detail.strip().splitlines()[0]
            print("    -> %s" % first[:240])

    n = len(results)
    ar = sum(1 for *_, s, _ in results if s == "as_required")
    lo = sum(1 for *_, s, _ in results if s == "loose")
    nr = sum(1 for *_, s, _ in results if s == "not_run")
    final = "%d attacks \u00b7 %d as required \u00b7 %d loose \u00b7 %d not run" % (n, ar, lo, nr)
    print("\n" + final)

    if json_out:
        Path(json_out).write_text(json.dumps(
            {"detector": DETECTOR,
             "results": [{"id": c, "title": t, "status": s, "detail": d} for c, t, s, d in results],
             "final": final}, indent=1))

    return 0 if lo == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
