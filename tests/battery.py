#!/usr/bin/env python3
"""Acceptance battery for closure_drift — the proofs pre-registered in PREREGISTRATION.md §2.

    python3 tests/battery.py                 # the detector one directory up
    python3 tests/battery.py DETECTOR        # another copy (the negative controls use this)
    python3 tests/battery.py --json OUT      # also write a machine-readable body

Each proof is green, red, or not_run with a named reason. Exit 0 when nothing is red, 1 when
something is, 2 when the battery itself could not run. Zero dependencies beyond CPython >= 3.9
and git. Every repository it measures is built in a temporary directory; nothing is read from
the clock into a result, so two runs give the same body.
"""
from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV = dict(os.environ,
           GIT_AUTHOR_NAME="battery", GIT_AUTHOR_EMAIL="battery@example.invalid",
           GIT_COMMITTER_NAME="battery", GIT_COMMITTER_EMAIL="battery@example.invalid",
           GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", PYTHONDONTWRITEBYTECODE="1")
ENV.pop("PYTHONIOENCODING", None)
PROOFS: list = []
DETECTOR = ""


class NotRun(Exception):
    pass


def proof(pid):
    def wrap(fn):
        PROOFS.append((pid, fn))
        return fn
    return wrap


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


class Repo:
    """A synthetic repository with deterministic dates: one day per commit or tag."""

    def __init__(self, root: Path, name: str):
        self.path = root / name
        self.path.mkdir()
        self.day = 0
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")

    def env(self):
        self.day += 1
        when = "2020-01-%02dT12:00:00+00:00" % self.day
        return dict(ENV, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)

    def git(self, *args, check_rc=True):
        r = subprocess.run(["git", *args], cwd=self.path, capture_output=True, env=self.env())
        if check_rc and r.returncode != 0:
            raise RuntimeError("git %s: %s" % (args[0], r.stderr.decode("utf-8", "replace")[:200]))
        return r.stdout.decode("utf-8", "replace").strip()

    def write(self, rel, data):
        target = self.path / rel if isinstance(rel, str) else Path(os.fsdecode(os.fsencode(self.path) + b"/" + rel))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))

    def commit(self, msg="c"):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", msg)

    def tag(self, name, annotated=False):
        if annotated:
            self.git("tag", "-a", name, "-m", name)
        else:
            self.git("tag", name)

    def release(self, tag, version, files: dict):
        if version is not None:
            self.write("package.json", json.dumps({"version": version}) + "\n")
        for rel, data in files.items():
            self.write(rel, data)
        self.commit(tag)
        self.tag(tag)


def run(repo, *args, env=None, text=False):
    cmd = [sys.executable, DETECTOR, str(repo.path if isinstance(repo, Repo) else repo)]
    if not text:
        cmd.append("--json")
    r = subprocess.run([*cmd, *args], capture_output=True, env=env or ENV)
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    doc = None
    if not text:
        try:
            doc = json.loads(out)
        except ValueError:
            doc = None
    return r.returncode, doc, out, err


def expect(repo, verdict, code, *args, **fields):
    rc, doc, out, err = run(repo, *args)
    check(doc is not None, "no JSON report (exit %d): %s" % (rc, (err or out)[:160]))
    check(doc.get("verdict") == verdict, "verdict %r, required %r" % (doc.get("verdict"), verdict))
    check(rc == code, "exit %d, required %d" % (rc, code))
    for k, v in fields.items():
        check(doc.get(k) == v, "%s = %r, required %r" % (k, doc.get(k), v))
    return doc


def refusal(rc, out, err, needle=None):
    check(rc == 2, "exit %d, required 2" % rc)
    check("Traceback" not in err and "Traceback" not in out, "a traceback was printed")
    check(err.strip() or out.strip(), "no cause was named")
    if needle:
        check(needle.lower() in (err + out).lower(), "the cause does not mention %r: %s" % (needle, err[:160]))


def two_tags(root, name, v1="1.0.0", v2="1.0.0", path="src/a.py", same=False):
    r = Repo(root, name)
    r.release("v1", v1, {"src/keep.py": "k\n", path: "one\n"})
    r.release("v2", v2, {path: "one\n" if same else "two\n", "note.txt": "n\n"})
    return r


# ---------------------------------------------------------------- A — verdicts

@proof("A01")
def a01(root):
    expect(two_tags(root, "a01", "1.0.0", "1.1.0"), "clean", 0, labels=2)


@proof("A02")
def a02(root):
    expect(two_tags(root, "a02"), "drift", 1, labels=1, labels_covering_multiple_closures=1,
           max_closures_per_label=2)


@proof("A03")
def a03(root):
    expect(two_tags(root, "a03", same=True), "inconclusive", 2)


@proof("A04")
def a04(root):
    r = Repo(root, "a04")
    r.release("v1", "1.0.0", {"src/a.py": "x\n"})
    expect(r, "inconclusive", 2)


@proof("A05")
def a05(root):
    r = Repo(root, "a05")
    r.write("package.json", '{"version":"1"}\n')
    r.write("src/a.py", "x\n")
    r.commit()
    expect(r, "no_publication_points", 2)


@proof("A06")
def a06(root):
    r = Repo(root, "a06")
    r.write("package.json", '{"version":"1"}\n')
    for i in range(6):
        r.write("src/a.py", "state %d\n" % i)
        r.commit()
    expect(r, "drift", 1, "--at", "commits", labels=1, max_closures_per_label=6)


@proof("A07")
def a07(root):
    expect(two_tags(root, "a07", "1", "2"), "empty_closure", 2, "--closure", "nothing/**",
           points_with_empty_closure=2)


@proof("A08")
def a08(root):
    expect(two_tags(root, "a08", "1", "2"), "no_labels", 2, "--version-file", "package.json",
           "--version-regex", "nomatch-(x+)", points_without_label=2)


@proof("A09")
def a09(root):
    r = Repo(root, "a09")
    r.release("v1", "1", {"src/a.py": "1\n"})
    r.release("v2", "2", {"src/a.py": "2\n"})
    r.release("v3", "2", {"src/a.py": "3\n"})
    expect(r, "drift", 1, labels=2, labels_covering_multiple_closures=1)


# ---------------------------------------------------------------- B — what was not compared

@proof("B01")
def b01(root):
    r = Repo(root, "b01")
    r.release("v0", None, {"src/a.py": "0\n"})
    r.release("v0b", None, {"src/a.py": "0b\n"})
    r.release("v1", "1", {"src/a.py": "1\n"})
    r.release("v2", "2", {"src/a.py": "2\n"})
    expect(r, "clean", 0, "--version-file", "package.json", points_without_label=2,
           publication_points_compared=2)
    rc, _, out, _ = run(r, "--version-file", "package.json", text=True)
    check("2 declared no version label" in out, "the text report does not print the count")


@proof("B02")
def b02(root):
    r = Repo(root, "b02")
    r.release("v0", "0", {"README": "nothing in the closure yet\n"})
    r.release("v1", "1", {"src/a.py": "1\n"})
    r.release("v2", "2", {"src/a.py": "2\n"})
    expect(r, "clean", 0, points_with_empty_closure=1)


@proof("B03")
def b03(root):
    r = Repo(root, "b03")
    for i in range(5):
        r.release("v%d" % i, str(i), {"src/a.py": "%d\n" % i})
    expect(r, "clean", 0, "--max-commits", "3", publication_points_scanned=3, range_truncated=True)
    _, _, out, _ = run(r, "--max-commits", "3", text=True)
    check("outside --max-commits" in out, "the text report does not say the range was cut")


@proof("B04")
def b04(root):
    r = two_tags(root, "b04", "1", "2")
    oid = r.git("hash-object", "-w", "note.txt")
    r.git("tag", "a-key", oid)
    expect(r, "clean", 0, points_not_commits=1)


# ---------------------------------------------------------------- C — paths

def only_this_changes(root, name, rel):
    r = Repo(root, name)
    try:
        r.release("v1", "1.0.0", {"src/keep.py": "k\n", rel: "one\n"})
        r.release("v2", "1.0.0", {rel: "two\n"})
    except (OSError, RuntimeError, ValueError) as e:
        raise NotRun("this file system or git refuses the name: %s" % type(e).__name__)
    return r


@proof("C01")
def c01(root):
    expect(only_this_changes(root, "c01", "src/ação.py"), "drift", 1)


@proof("C02")
def c02(root):
    expect(only_this_changes(root, "c02", "src/with space\tand tab.py"), "drift", 1)


@proof("C03")
def c03(root):
    expect(only_this_changes(root, "c03", "src/line\nbreak.py"), "drift", 1)


@proof("C04")
def c04(root):
    r = Repo(root, "c04")
    r.write("package.json", '{"version":"1"}\n')
    r.write("src/keep.py", "k\n")
    r.git("add", "-A")
    r.git("update-index", "--add", "--cacheinfo", "160000," + "1" * 40 + ",src/sub")
    r.git("commit", "-q", "-m", "v1")
    r.tag("v1")
    r.git("update-index", "--add", "--cacheinfo", "160000," + "2" * 40 + ",src/sub")
    r.git("commit", "-q", "-m", "v2")
    r.tag("v2")
    expect(r, "drift", 1)


def old_formula(repo, ref, include, exclude):
    """The closure as 0.3.0 through 0.7.1 computed it, written here independently."""
    def m(path, globs):
        return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path, g.replace("**/", "*/"))
                   or (g.endswith("/**") and path.startswith(g[:-3] + "/")) for g in globs)
    h = hashlib.sha256()
    for line in repo.git("ls-tree", "-r", ref).splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) < 3 or parts[1] != "blob" or not m(path, include) or m(path, exclude):
            continue
        h.update(path.encode())
        h.update(parts[2].encode())
    return h.hexdigest()[:16]


@proof("C05")
def c05(root):
    r = Repo(root, "c05")
    r.release("v1", "1.0.0", {"src/a.py": "1\n", "lib/b.js": "1\n", "top.py": "1\n",
                              "src/tests/t.py": "t\n", "docs/d.md": "d\n"})
    r.release("v2", "1.0.0", {"src/a.py": "2\n", "src/deep/er/c.rs": "c\n"})
    doc = expect(r, "drift", 1)
    include = ["src/**", "lib/**", "app/**", "*.py", "*.js", "*.ts", "*.rs", "*.go", "*.java"]
    exclude = ["**/test/**", "**/tests/**", "**/*_test.*", "**/*.test.*", "**/spec/**",
               "**/docs/**", "**/*.md", "**/node_modules/**", "**/vendor/**", "**/.git/**"]
    want = {old_formula(r, "v1", include, exclude), old_formula(r, "v2", include, exclude)}
    got = set(doc["drift"]["1.0.0"])
    check(got == want, "closures %s differ from the 0.3.0-0.7.1 formula %s" % (sorted(got), sorted(want)))


@proof("C06")
def c06(root):
    if os.name == "nt":
        raise NotRun("file names are not byte strings on this platform")
    expect(only_this_changes(root, "c06", b"src/not-utf8-\xff.py"), "drift", 1)


# ---------------------------------------------------------------- D — refusals

@proof("D01")
def d01(root):
    d = root / "d01"
    d.mkdir()
    rc, _, out, err = run(d)
    refusal(rc, out, err, "not a git repository")


def with_config(root, name, raw: bytes):
    r = two_tags(root, name, "1", "2")
    (r.path / ".closure-drift.json").write_bytes(raw)
    return run(r)


@proof("D02")
def d02(root):
    rc, _, out, err = with_config(root, "d02", b"[]")
    refusal(rc, out, err, "object")


@proof("D03")
def d03(root):
    rc, _, out, err = with_config(root, "d03", b"\xff\xfe{}")
    refusal(rc, out, err, "broken")


@proof("D04")
def d04(root):
    rc, _, out, err = with_config(root, "d04", b"{not json")
    refusal(rc, out, err, "broken")


@proof("D05")
def d05(root):
    rc, _, out, err = with_config(root, "d05", b'{"closures": ["src/**"]}')
    refusal(rc, out, err, "unknown key")


@proof("D06")
def d06(root):
    rc, _, out, err = with_config(root, "d06", b'{"closure": "src/**"}')
    refusal(rc, out, err, "closure")


@proof("D07")
def d07(root):
    rc, _, out, err = with_config(root, "d07", b'{"at": "weekly"}')
    refusal(rc, out, err, "at")


@proof("D08")
def d08(root):
    rc, _, out, err = run(two_tags(root, "d08"), "--version-file", "package.json", "--version-regex", "(")
    refusal(rc, out, err, "invalid --version-regex")


@proof("D09")
def d09(root):
    rc, _, out, err = run(two_tags(root, "d09"), "--version-file", "package.json", "--version-regex", "version")
    refusal(rc, out, err, "capture group")


@proof("D10")
def d10(root):
    rc, _, out, err = run(two_tags(root, "d10"), "--version-regex", "v(\\d+)")
    refusal(rc, out, err, "--version-file")


@proof("D11")
def d11(root):
    r = two_tags(root, "d11")
    for value in ("0", "-3"):
        rc, _, out, err = run(r, "--max-commits", value)
        refusal(rc, out, err, "--max-commits")


@proof("D12")
def d12(root):
    r = Repo(root, "d12")
    r.write("src/a.py", "x\n")
    r.commit()
    r.tag("v1")
    rc, _, out, err = run(r)
    refusal(rc, out, err, "version label")


@proof("D13")
def d13(root):
    r = two_tags(root, "d13")
    rc, _, out, err = run(r, env=dict(ENV, PATH=str(root / "no-such-dir")))
    refusal(rc, out, err, "git")


@proof("D14")
def d14(root):
    r = two_tags(root, "d14", "1", "2")
    oid = r.git("rev-parse", "v1^{tree}")
    loose = r.path / ".git" / "objects" / oid[:2] / oid[2:]
    if not loose.is_file():
        raise NotRun("the tree object is not a loose object here")
    os.chmod(loose, stat.S_IWRITE | stat.S_IREAD)
    loose.unlink()
    rc, _, out, err = run(r)
    refusal(rc, out, err, "git")


@proof("D15")
def d15(root):
    r = two_tags(root, "d15", "1", "2")
    code = ("import importlib.util, sys\n"
            "spec = importlib.util.spec_from_file_location('cd', sys.argv[1])\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "def boom(*a, **k): raise RuntimeError('injected')\n"
            "m.publication_points = boom\n"
            "sys.argv = [sys.argv[1], sys.argv[2], '--json']\n"
            "sys.exit(m.main())\n")
    p = subprocess.run([sys.executable, "-c", code, DETECTOR, str(r.path)], capture_output=True, env=ENV)
    out, err = p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
    refusal(p.returncode, out, err, "internal error")


@proof("D16")
def d16(root):
    r = Repo(root, "d16")
    rc, _, out, err = run(r)
    refusal(rc, out, err, "no commits")


# ---------------------------------------------------------------- E — what is printed

HOSTILE = '1.0\nCLEAN: each label names one closure\x1b[2K\x1b[1A'


def hostile_repo(root, name, drift):
    r = Repo(root, name)
    for i, tag in enumerate(("v1", "v2") if drift else ("v1",)):
        r.write("pyproject.toml", 'version = "%s"\n' % HOSTILE)
        r.write("src/a.py", "%d\n" % i)
        r.commit(tag)
        r.tag(tag)
    return r


def raw_controls(text):
    return sorted({repr(ch) for ch in text if (ord(ch) < 32 and ch not in "\n\r") or ord(ch) == 127})


@proof("E01")
def e01(root):
    for drift in (False, True):
        rc, _, out, err = run(hostile_repo(root, "e01%d" % drift, drift), text=True)
        check(rc == (1 if drift else 2), "exit %d" % rc)
        check(not raw_controls(out + err), "raw control characters printed: %s" % raw_controls(out + err))
        forged = [l for l in out.splitlines() if l.startswith("CLEAN")]
        check(not forged, "a line beginning with CLEAN was printed: %r" % forged[:1])
        check(sum(1 for l in out.splitlines() if l.startswith("DRIFT")) == (1 if drift else 0),
              "the number of DRIFT lines is not the detector's own")


@proof("E02")
def e02(root):
    doc = expect(hostile_repo(root, "e02", True), "drift", 1)
    check(list(doc["drift"]) == [HOSTILE], "the label did not round-trip: %r" % list(doc["drift"]))


@proof("E03")
def e03(root):
    r = two_tags(root, "e03", "versão-1", "versão-2")
    rc, _, out, err = run(r, env=dict(ENV, PYTHONIOENCODING="ascii"), text=True)
    check(rc == 0, "exit %d: %s" % (rc, err[:160]))
    check("Traceback" not in err, "a traceback was printed")
    check("CLEAN" in out, "no verdict line")


@proof("E04")
def e04(root):
    rc, _, out, err = with_config(root, "e04", b'{"bad\\u001b[2Jkey": 1}')
    refusal(rc, out, err, "unknown key")
    check(not raw_controls(out + err), "raw control characters in the refusal")


# ---------------------------------------------------------------- F — what it does to the machine

def sh_touch(marker: Path) -> str:
    return "touch '%s'" % marker.as_posix()


@proof("F01")
def f01(root):
    r = two_tags(root, "f01", "1", "2")
    marker = root / "f01-marker"
    r.git("config", "core.fsmonitor", sh_touch(marker) + "; false")
    rc, doc, _, err = run(r)
    check(not marker.exists(), "the command in core.fsmonitor was executed")
    check(rc == 0 and doc and doc["verdict"] == "clean", "the measurement did not complete: %s" % err[:120])


@proof("F02")
def f02(root):
    r = Repo(root, "f02")
    r.release("v1", "1", {"src/a.py": "1\n", ".gitattributes": "*.py filter=x\n"})
    r.release("v2", "2", {"src/a.py": "2\n"})
    marker = root / "f02-marker"
    r.git("config", "filter.x.clean", sh_touch(marker) + "; cat")
    r.write("src/a.py", "modified, and routed through the filter\n")
    if marker.exists():
        marker.unlink()
    rc, doc, _, err = run(r)
    check(not marker.exists(), "the clean filter was executed")
    check(rc == 0 and doc, "the measurement did not complete: %s" % err[:120])
    check(doc["stamp"]["working_tree_dirty"] is None, "working_tree_dirty is %r, required null"
          % (doc["stamp"]["working_tree_dirty"],))
    check("filter.x.clean" in doc["stamp"].get("working_tree_dirty_note", ""), "the report does not say why")


def snapshot(path: Path) -> str:
    h = hashlib.sha256()
    for folder, dirs, files in os.walk(path):
        dirs.sort()
        for name in sorted(files):
            full = Path(folder) / name
            h.update(str(full.relative_to(path)).encode("utf-8", "surrogateescape"))
            h.update(hashlib.sha256(full.read_bytes()).digest())
    return h.hexdigest()


@proof("F03")
def f03(root):
    r = two_tags(root, "f03", "1", "2")
    r.write("src/keep.py", "k\n")                      # same bytes, new timestamp: stat-dirty
    os.utime(r.path / "src" / "keep.py", (1, 1))
    r.write("src/a.py", "really modified\n")
    before = snapshot(r.path)
    for args in ((), ("--at", "commits")):
        run(r, *args)
        run(r, *args, text=True)
    check(snapshot(r.path) == before, "a file under the repository changed during the measurement")


@proof("F04")
def f04(root):
    src = Path(DETECTOR).read_text(encoding="utf-8")
    allowed = {"__future__", "argparse", "fnmatch", "hashlib", "json", "os", "re", "subprocess",
               "sys", "collections", "pathlib"}
    found = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            found |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            found.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("__import__", "eval", "exec"):
            raise AssertionError("the detector calls %s" % node.func.id)
    check(found <= allowed, "imports outside the allowed set: %s" % sorted(found - allowed))
    starts = [l.strip() for l in src.splitlines() if "subprocess." in l and not l.strip().startswith("#")]
    check(len(starts) == 1 and "[*GIT," in starts[0], "a program other than git may be started: %r" % starts)
    check("os.system" not in src and "os.popen" not in src and "os.exec" not in src, "os.* process call")


# ---------------------------------------------------------------- G — stamp and determinism

@proof("G01")
def g01(root):
    r = two_tags(root, "g01")
    for text in (False, True):
        a, b = run(r, text=text), run(r, text=text)
        check(a[2] == b[2] and a[0] == b[0], "two runs differ (%s)" % ("text" if text else "json"))


@proof("G02")
def g02(root):
    doc = expect(two_tags(root, "g02"), "drift", 1)
    want = hashlib.sha256(Path(DETECTOR).read_bytes()).hexdigest()[:16]
    check(doc["stamp"]["detector_closure"] == want, "detector_closure %r, required %r"
          % (doc["stamp"]["detector_closure"], want))


@proof("G03")
def g03(root):
    r = two_tags(root, "g03")
    check(expect(r, "drift", 1)["stamp"]["working_tree_dirty"] is False, "a clean tree is not reported clean")
    r.write("src/a.py", "modified\n")
    check(expect(r, "drift", 1)["stamp"]["working_tree_dirty"] is True, "a modified tree is not reported dirty")


# ---------------------------------------------------------------- H–K

@proof("H01")
def h01(root):
    p = subprocess.run([sys.executable, str(HERE / "fixture_label_only.py"), DETECTOR],
                       capture_output=True, env=ENV)
    check(p.returncode == 0, "the fixture ended at %d: %s"
          % (p.returncode, p.stdout.decode("utf-8", "replace")[:200]))


def config_repo(root, name):
    r = Repo(root, name)
    r.write("package.json", '{"version":"1"}\n')
    r.write(".closure-drift.json", json.dumps({"at": "commits", "closure": ["edition.txt"]}))
    for i in range(3):
        r.write("edition.txt", "%d\n" % i)
        r.commit()
    return r


@proof("I01")
def i01(root):
    expect(config_repo(root, "i01"), "no_publication_points", 2, "--at", "tags")


@proof("I02")
def i02(root):
    doc = expect(config_repo(root, "i02"), "drift", 1, max_closures_per_label=3)
    check(doc["published_at"] == "commits" and doc["closure_globs"] == ["edition.txt"],
          "the settings of the config file were not the ones used")


@proof("J01")
def j01(root):
    r = Repo(root, "j01")
    for tag, v in (("v1", "1.2.3"), ("v2", "1.2.4")):
        r.write("pyproject.toml", '[project]\nname = "pkg"\ndynamic = ["version"]\n')
        r.write("pkg/__init__.py", '__version__ = "%s"\n' % v)
        r.write("pkg/core.py", "# %s\n" % v)
        r.commit(tag)
        r.tag(tag)
    doc = expect(r, "clean", 0, "--closure", "pkg/**", labels=2)
    check(doc["version_file"] == "pkg/__init__.py", "label read from %r" % doc["version_file"])


@proof("K01")
def k01(root):
    r = Repo(root, "k01")
    r.write("package.json", '{"version":"1"}\n')
    r.write("src/a.py", "1\n")
    r.commit()
    r.tag("v1", annotated=True)
    r.write("package.json", '{"version":"2"}\n')
    r.write("src/a.py", "2\n")
    r.commit()
    r.tag("v2")
    expect(r, "clean", 0, publication_points_scanned=2, labels=2)


# ---------------------------------------------------------------- runner

def remove(path):
    def force(fn, p, _exc):
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        fn(p)
    shutil.rmtree(path, onerror=force)


def main() -> int:
    global DETECTOR
    args = sys.argv[1:]
    out_json = None
    if "--json" in args:
        i = args.index("--json")
        out_json = args[i + 1]
        del args[i:i + 2]
    DETECTOR = os.path.abspath(args[0]) if args else str(HERE.parent / "closure_drift.py")
    if not os.path.isfile(DETECTOR):
        print("cannot run: no detector at %s" % DETECTOR, file=sys.stderr)
        return 2
    if shutil.which("git") is None:
        print("cannot run: git is not on PATH", file=sys.stderr)
        return 2
    results = []
    for pid, fn in PROOFS:
        root = Path(tempfile.mkdtemp(prefix="cd-battery-"))
        try:
            fn(root)
            status, detail = "green", ""
        except NotRun as e:
            status, detail = "not_run", str(e)
        except AssertionError as e:
            status, detail = "red", str(e)
        except Exception as e:  # noqa: BLE001 — a proof that cannot be set up is red, and says why
            status, detail = "red", "the proof could not be carried out: %s: %s" % (type(e).__name__, str(e)[:160])
        finally:
            remove(root)
        results.append({"id": pid, "status": status, "detail": detail})
        print("%-4s %-8s %s" % (pid, status, detail))
    count = {s: sum(1 for r in results if r["status"] == s) for s in ("green", "red", "not_run")}
    if out_json:
        with open(out_json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"proofs": results, "totals": count}, fh, indent=1, sort_keys=True)
            fh.write("\n")
    digest = hashlib.sha256(Path(DETECTOR).read_bytes()).hexdigest()[:16]
    print("\ndetector: %s (sha256 %s)" % (os.path.basename(DETECTOR), digest))
    print("%d declared · %d green · %d red · %d not run"
          % (len(results), count["green"], count["red"], count["not_run"]))
    return 1 if count["red"] else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
