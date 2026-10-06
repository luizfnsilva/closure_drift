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

    def __init__(self, root: Path, name: str, object_format: str = ""):
        self.path = root / name
        self.path.mkdir()
        self.day = 0
        if object_format:
            self.git("init", "-q", "--object-format=" + object_format)
        else:
            self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")

    def env(self):
        self.day += 1
        when = "2020-01-%02dT12:00:00+00:00" % self.day
        return dict(ENV, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)

    def git(self, *args, check_rc=True):
        r = subprocess.run(["git", *args], cwd=self.path, capture_output=True, env=self.env(),
                           stdin=subprocess.DEVNULL)
        if check_rc and r.returncode != 0:
            raise RuntimeError("git %s: %s" % (args[0], r.stderr.decode("utf-8", "replace")[:200]))
        return r.stdout.decode("utf-8", "replace").strip()

    def write(self, rel, data):
        target = self.path / rel if isinstance(rel, str) else Path(os.fsdecode(os.fsencode(self.path) + b"/" + rel))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))

    def remove(self, rel):
        (self.path / rel).unlink()

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
    r = subprocess.run([*cmd, *args], capture_output=True, env=env or ENV, stdin=subprocess.DEVNULL)
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
    rc, doc, out, err = run(r)
    check(doc is None, "a report was produced (verdict %r): the unreadable tag was taken as an answer"
          % (doc or {}).get("verdict"))
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
        rc, _, out, err = run(hostile_repo(root, "e01%d" % drift, drift), "--version-file", "pyproject.toml", text=True)
        check(rc == (1 if drift else 2), "exit %d" % rc)
        check(not raw_controls(out + err), "raw control characters printed: %s" % raw_controls(out + err))
        forged = [l for l in out.splitlines() if l.startswith("CLEAN")]
        check(not forged, "a line beginning with CLEAN was printed: %r" % forged[:1])
        check(sum(1 for l in out.splitlines() if l.startswith("DRIFT")) == (1 if drift else 0),
              "the number of DRIFT lines is not the detector's own")


@proof("E02")
def e02(root):
    doc = expect(hostile_repo(root, "e02", True), "drift", 1, "--version-file", "pyproject.toml")
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
               "sys", "collections", "pathlib", "shlex", "unicodedata", "ast", "warnings"}
    found = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            found |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            found.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("__import__", "eval", "exec"):
            raise AssertionError("the detector calls %s" % node.func.id)
    check(found <= allowed, "imports outside the allowed set: %s" % sorted(found - allowed))
    starts = [l.strip() for l in src.splitlines()
              if ("subprocess.run(" in l or "subprocess.Popen(" in l) and not l.strip().startswith("#")]
    allowed_starts = ("[*GIT,", "[sys.executable, os.path.abspath(__file__), \"--match-on-stdin\"]")
    stray = [l for l in starts if not any(a in l for a in allowed_starts)]
    check(len(starts) >= 3 and not stray,
          "a program other than git, or the detector itself for a pattern match, may be started: %r" % stray)
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


# ---------------------------------------------------------------- D17 — added after the adversarial campaign

@proof("D17")
def d17(root):
    r = Repo(root, "d17")
    for i, tag in enumerate(("v1", "v2")):
        r.write("evil.txt", "version=" + "a" * 40 + "!\n")
        r.write("src/a.py", "%d\n" % i)
        r.commit(tag)
        r.tag(tag)
    (r.path / ".closure-drift.json").write_text(
        json.dumps({"version_file": "evil.txt", "version_regex": "(a+)+$"}), encoding="utf-8")
    cmd = [sys.executable, DETECTOR, str(r.path), "--json"]
    try:
        p = subprocess.run(cmd, capture_output=True, env=ENV, timeout=90)
    except subprocess.TimeoutExpired:
        raise AssertionError("the detector was still running after 90 seconds")
    refusal(p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace"),
            "did not finish")


# ---------------------------------------------------------------- R — report format

@proof("R01")
def r01(root):
    doc = expect(two_tags(root, "r01a"), "drift", 1)
    check(doc.get("report_format") == 2, "report_format = %r" % doc.get("report_format"))
    r = Repo(root, "r01b")
    r.write("package.json", '{"version":"1"}\n')
    r.write("src/a.py", "x\n")
    r.commit()
    doc = expect(r, "no_publication_points", 2)
    check(doc.get("report_format") == 2, "report_format missing from the refusal report")


# ---------------------------------------------------------------- W — would-tag

def head_after(root, name, tags, head_version, head_file):
    """tags: [(tag, version, content of src/a.py)]; then one more commit, untagged."""
    r = Repo(root, name)
    for tag, version, content in tags:
        r.release(tag, version, {"src/a.py": content})
    r.write("package.json", json.dumps({"version": head_version}) + "\n")
    r.write("src/a.py", head_file)
    r.commit("head")
    return r


@proof("W01")
def w01(root):
    r = head_after(root, "w01", [("v1", "1", "1\n"), ("v2", "2", "2\n")], "3", "3\n")
    expect(r, "would_be_clean", 0, "--would-tag", label_at_head="3")


@proof("W02")
def w02(root):
    r = head_after(root, "w02", [("v1", "1", "1\n"), ("v2", "2", "2\n")], "2", "changed\n")
    doc = expect(r, "would_drift", 1, "--would-tag", label_at_head="2")
    check(len(doc["collides_with"]) == 1 and doc["collides_with"][0].startswith("v2 "),
          "the report does not name the tag: %r" % doc["collides_with"])


@proof("W03")
def w03(root):
    r = head_after(root, "w03", [("v1", "1", "1\n"), ("v2", "2", "2\n")], "2", "2\n")
    expect(r, "would_be_clean", 0, "--would-tag")


@proof("W04")
def w04(root):
    r = Repo(root, "w04")
    r.write("package.json", '{"version":"1"}\n')
    r.write("src/a.py", "x\n")
    r.commit()
    expect(r, "would_be_clean", 0, "--would-tag")


@proof("W05")
def w05(root):
    r = head_after(root, "w05", [("v1", "1", "1\n")], "9", "9\n")
    r.write("package.json", "{}\n")
    r.commit("no label")
    expect(r, "no_label_at_head", 2, "--would-tag", "--version-file", "package.json")


@proof("W06")
def w06(root):
    r = head_after(root, "w06", [("v1", "1", "1\n")], "2", "2\n")
    expect(r, "empty_closure_at_head", 2, "--would-tag", "--closure", "nothing/**")


@proof("W07")
def w07(root):
    rc, _, out, err = run(two_tags(root, "w07"), "--would-tag", "--at", "commits")
    refusal(rc, out, err, "--would-tag")


@proof("W08")
def w08(root):
    r = head_after(root, "w08", [("v1", "1", "1\n"), ("v2", "1", "other\n")], "2", "2\n")
    expect(r, "would_be_clean", 0, "--would-tag", existing_drift_labels=1)


@proof("W09")
def w09(root):
    r = head_after(root, "w09", [("v1", "1", "1\n"), ("v2", "2", "2\n")], "2", "2\n")
    r.write("src/a.py", "edited, not committed\n")
    doc = expect(r, "would_be_clean", 0, "--would-tag")
    check(doc["stamp"]["working_tree_dirty"] is True, "the modified tree is not reported")
    _, _, out, _ = run(r, "--would-tag", text=True)
    check("the commit is measured, not the modified working tree" in out, "the text report does not say so")


# ---------------------------------------------------------------- T — tags

def families(root, name):
    r = Repo(root, name)
    r.release("rs-1", "1", {"src/a.py": "rust build\n"})
    r.release("py-1", "1", {"src/a.py": "python build\n"})
    r.release("py-2", "2", {"src/a.py": "python build 2\n"})
    return r


@proof("T01")
def t01(root):
    r = families(root, "t01")
    expect(r, "drift", 1)
    expect(r, "clean", 0, "--tags", "py-*", labels=2)


@proof("T02")
def t02(root):
    rc, _, out, err = run(families(root, "t02"), "--tags", "nothing-*", text=True)
    refusal(rc, out, err, "nothing-*")


@proof("T03")
def t03(root):
    r = families(root, "t03")
    (r.path / ".closure-drift.json").write_text(json.dumps({"tags": ["py-*"]}), encoding="utf-8")
    expect(r, "clean", 0)
    expect(r, "drift", 1, "--tags", "*-1")


@proof("T04")
def t04(root):
    expect(families(root, "t04"), "clean", 0, "--tags", "py-*", tag_globs=["py-*"], tags_filtered_out=1)


@proof("T05")
def t05(root):
    rc, _, out, err = run(families(root, "t05"), "--tags", "py-*", "--at", "commits")
    refusal(rc, out, err, "--tags")


# ---------------------------------------------------------------- S — strict

def half_labelled(root, name):
    r = Repo(root, name)
    r.release("v0", None, {"src/a.py": "0\n"})
    r.release("v0b", None, {"src/a.py": "0b\n"})
    r.release("v1", "1", {"src/a.py": "1\n"})
    r.release("v2", "2", {"src/a.py": "2\n"})
    return r


@proof("S01")
def s01(root):
    expect(half_labelled(root, "s01"), "incomplete", 2, "--version-file", "package.json", "--strict")


@proof("S02")
def s02(root):
    expect(two_tags(root, "s02", "1", "2"), "clean", 0, "--strict")


@proof("S03")
def s03(root):
    expect(two_tags(root, "s03"), "drift", 1, "--strict")


@proof("S04")
def s04(root):
    r = Repo(root, "s04")
    for i in range(5):
        r.release("v%d" % i, str(i), {"src/a.py": "%d\n" % i})
    expect(r, "incomplete", 2, "--max-commits", "3", "--strict")


# ---------------------------------------------------------------- X — explain

def three_way(root, name, odd="src/a.py"):
    r = Repo(root, name)
    try:
        r.release("v1", "1.0.0", {odd: "one\n", "src/gone.py": "g\n", "src/same.py": "s\n"})
        r.remove("src/gone.py")
        r.release("v2", "1.0.0", {odd: "two\n", "src/new.py": "n\n"})
    except (OSError, RuntimeError, ValueError) as e:
        raise NotRun("this file system or git refuses the name: %s" % type(e).__name__)
    return r


@proof("X01")
def x01(root):
    doc = expect(three_way(root, "x01"), "drift", 1, "--explain", "1.0.0")
    other = doc["explain"]["others"][0]
    got = (other["changed"], other["only_in_first"], other["only_in_other"])
    check(got == (["src/a.py"], ["src/gone.py"], ["src/new.py"]), "explain lists %r" % (got,))


@proof("X02")
def x02(root):
    r = three_way(root, "x02")
    rc, _, out, err = run(r, "--explain", "9.9.9")
    refusal(rc, out, err, "--explain")
    rc, _, out, err = run(two_tags(root, "x02b", "1", "2"), "--explain", "1")
    refusal(rc, out, err, "--explain")


@proof("X03")
def x03(root):
    r = three_way(root, "x03", odd="src/odd\n\x1b[2Kname.py")
    rc, _, out, err = run(r, "--explain", "1.0.0", text=True)
    check(rc == 1, "exit %d" % rc)
    check(not raw_controls(out + err), "raw control characters printed: %s" % raw_controls(out + err))


@proof("X04")
def x04(root):
    r = three_way(root, "x04")
    for text in (False, True):
        _, _, out, err = run(r, text=text)
        for path in ("src/a.py", "src/gone.py", "src/new.py", "src/same.py", "gone.py", "same.py"):
            check(path not in out + err, "a path of the closure is in the %s report: %s"
                  % ("text" if text else "JSON", path))


# ---------------------------------------------------------------- U — identity of a closure

@proof("U01")
def u01(root):
    doc = expect(two_tags(root, "u01"), "drift", 1)
    keys = set(doc["drift"]["1.0.0"])
    check(keys == set(doc["closure_ids"]), "closure_ids does not cover the closures in drift")
    check(all(len(v) == 64 and int(v, 16) >= 0 for v in doc["closure_ids"].values()), "not 64 hex")
    check(len(set(doc["closure_ids"].values())) == len(keys), "two closures share a full id")


@proof("U02")
def u02(root):
    r = Repo(root, "u02")
    r.release("v1", "1.0.0", {"src/a": "content A\n", "src/b": "content B\n"})
    x = r.git("rev-parse", "v1:src/a")
    r.remove("src/a")
    r.remove("src/b")
    try:
        r.release("v2", "1.0.0", {"src/a%ssrc/b" % x: "content B\n"})
    except (OSError, RuntimeError) as e:
        raise NotRun("this file system refuses the path: %s" % type(e).__name__)
    include = ["src/**"]
    a, b = old_formula(r, "v1", include, []), old_formula(r, "v2", include, [])
    check(a == b, "the two trees do not collide under the earlier construction (%s, %s): "
          "the proof would show nothing" % (a, b))
    expect(r, "drift", 1, "--closure", "src/**")


# ---------------------------------------------------------------- P — reading trees

def load_detector():
    import importlib.util
    spec = importlib.util.spec_from_file_location("detector_under_test", DETECTOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@proof("P01")
def p01(root):
    r = Repo(root, "p01")
    r.write("package.json", '{"version":"1"}\n')
    r.write("a/b/c/deep.py", "d\n")
    r.write("a/b.txt", "sibling that sorts around the folder a/b\n")
    r.write("a/b-c.txt", "x\n")
    r.write("z.py", "z\n")
    try:
        r.write("src/ação.py", "n\n")
    except OSError:
        pass
    r.git("add", "-A")
    r.git("update-index", "--add", "--cacheinfo", "160000," + "3" * 40 + ",a/sub")
    blob = r.git("hash-object", "-w", "z.py")
    r.git("update-index", "--add", "--cacheinfo", "120000,%s,a/link" % blob)
    r.git("update-index", "--add", "--cacheinfo", "100755,%s,a/run.sh" % blob)
    r.git("commit", "-q", "-m", "one")
    r.write("a/b/c/deep.py", "changed\n")
    r.write("new/dir/file.rs", "r\n")
    r.git("add", "a/b/c/deep.py", "new/dir/file.rs")
    r.git("commit", "-q", "-m", "two")
    module = load_detector()
    check(hasattr(module, "Objects"), "the detector has no tree reader to compare")
    objects = module.Objects(str(r.path))
    try:
        for ref in ("HEAD~1", "HEAD"):
            sha = r.git("rev-parse", ref)
            raw = subprocess.run(["git", "ls-tree", "-r", "-z", sha], cwd=r.path, capture_output=True,
                                 env=ENV).stdout
            want = []
            for record in raw.split(b"\0"):
                if record:
                    meta, _, path = record.partition(b"\t")
                    want.append((path.decode("utf-8", "surrogateescape"), meta.split()[1].decode(),
                                 meta.split()[2].decode()))
            got = objects.entries(sha)
            check(got == want, "entries differ from ls-tree at %s: %d against %d, first difference %r"
                  % (ref, len(got), len(want), next((p for p in zip(got, want) if p[0] != p[1]), None)))
            check(len(want) >= 8, "the tree is too small to show anything")
    finally:
        objects.close()


@proof("P02")
def p02(root):
    try:
        r = Repo(root, "p02", object_format="sha256")
    except RuntimeError:
        raise NotRun("this git cannot create a sha256 repository")
    r.release("v1", "1", {"src/a.py": "1\n", "src/deep/b.py": "b\n"})
    r.release("v2", "2", {"src/a.py": "2\n"})
    expect(r, "clean", 0)
    r.release("v3", "2", {"src/deep/b.py": "changed\n"})
    expect(r, "drift", 1)


# ---------------------------------------------------------------- G04 — badge

@proof("G04")
def g04(root):
    r = two_tags(root, "g04")
    rc, _, out, err = run(r, "--badge", text=True)
    head = r.git("rev-parse", "HEAD")[:12]
    lines = out.splitlines()
    check(rc == 1, "exit %d, required 1" % rc)
    check(len(lines) == 1 and not err.strip(), "more than one line was printed")
    check(lines[0].startswith("![version labels: drift @ %s](https://img.shields.io/badge/" % head),
          "the badge does not name the verdict and the commit: %r" % lines[0][:80])


# ---------------------------------------------------------------- CMP — compare two references

@proof("CMP01")
def cmp01(root):
    doc = expect(three_way(root, "cmp01"), "differs_under_one_label", 1, "--compare", "v1", "v2")
    got = (doc["changed"], doc["only_in_a"], doc["only_in_b"])
    check(got == (["src/a.py"], ["src/gone.py"], ["src/new.py"]), "compare lists %r" % (got,))
    check(doc["a"]["label"] == doc["b"]["label"] == "1.0.0" and doc["mode"] == "compare", "sides are wrong")


@proof("CMP02")
def cmp02(root):
    expect(two_tags(root, "cmp02", "1", "2"), "differs_under_two_labels", 0, "--compare", "v1", "v2")


@proof("CMP03")
def cmp03(root):
    doc = expect(two_tags(root, "cmp03", same=True), "identical", 0, "--compare", "v1", "v2")
    check(doc["changed"] == doc["only_in_a"] == doc["only_in_b"] == [], "the lists are not empty")


@proof("CMP04")
def cmp04(root):
    rc, _, out, err = run(two_tags(root, "cmp04"), "--compare", "v1", "no-such-ref")
    refusal(rc, out, err, "no-such-ref")


@proof("CMP05")
def cmp05(root):
    r = half_labelled(root, "cmp05")
    doc = expect(r, "not_comparable", 2, "--compare", "v0", "v1", "--version-file", "package.json")
    check(doc["a"]["label"] is None and doc["changed"] == ["src/a.py"], "label or paths are wrong")


@proof("CMP06")
def cmp06(root):
    odd = "src/odd\n\x1b[2Kname.py"
    r = three_way(root, "cmp06", odd=odd)
    rc, _, out, err = run(r, "--compare", "v1", "v2", text=True)
    check(rc == 1, "exit %d" % rc)
    check(not raw_controls(out + err), "raw control characters printed: %s" % raw_controls(out + err))
    doc = expect(r, "differs_under_one_label", 1, "--compare", "v1", "v2")
    check(doc["changed"] == [odd], "the path did not round-trip: %r" % doc["changed"])


@proof("CMP07")
def cmp07(root):
    r = two_tags(root, "cmp07")
    for extra in (("--would-tag",), ("--explain", "1.0.0"), ("--at", "commits")):
        rc, _, out, err = run(r, "--compare", "v1", "v2", *extra)
        refusal(rc, out, err, "--compare")


# ---------------------------------------------------------------- DG — diagnose

@proof("DG01")
def dg01(root):
    r = two_tags(root, "dg01", "1.7.7-label", "1.7.7-label")
    rc0, _, out0, _ = run(r, text=True)
    rc, _, out, err = run(r, "--diagnose", text=True)
    check(rc == rc0 == 1, "exit %d with --diagnose, %d without" % (rc, rc0))
    block = out.split("\nrepository   ", 1)[0]
    module = load_detector()
    digest = hashlib.sha256(Path(DETECTOR).read_bytes()).hexdigest()[:16]
    for needle in ("closure_drift " + module.__version__, digest, "Python " + sys.version.split()[0], "git version"):
        check(needle in block, "the block does not name %r" % needle)
    for secret in ("1.7.7-label", "src/a.py", "keep.py", str(r.path), r.path.name):
        check(secret not in block, "the block holds %r" % secret)
    check(out.split("\nrepository   ", 1)[1].split("Measured at HEAD")[0]
          == out0.split("repository   ", 1)[1].split("Measured at HEAD")[0], "the report itself changed")


@proof("DG02")
def dg02(root):
    doc = expect(two_tags(root, "dg02"), "drift", 1, "--diagnose")
    d = doc.get("diagnostics") or {}
    want = {"detector_version", "detector_closure", "python", "git", "platform", "options", "repository"}
    check(want <= set(d), "diagnostics lacks %s" % sorted(want - set(d)))
    check(d["repository"]["tags"] == 2 and d["repository"]["bare"] == "false", "repository facts are wrong: %r" % d["repository"])


@proof("DG03")
def dg03(root):
    d = root / "dg03"
    d.mkdir()
    rc, _, out, err = run(d, "--diagnose", text=True)
    check(rc == 2, "exit %d" % rc)
    check("diagnostics " in out and "git version" in out, "the block was not printed before the refusal")
    check("not a git repository" in err and "Traceback" not in err, "the refusal is not the named one")


# ---------------------------------------------------------------- VER — version

@proof("VER01")
def ver01(root):
    p = subprocess.run([sys.executable, DETECTOR, "--version"], capture_output=True, env=ENV,
                       stdin=subprocess.DEVNULL)
    out = p.stdout.decode("utf-8", "replace")
    check(p.returncode == 0, "exit %d" % p.returncode)
    check(out.strip() == "closure_drift " + load_detector().__version__ and not p.stderr.strip(),
          "printed %r" % out)


# ---------------------------------------------------------------- TV — a version derived from the tag

@proof("TV01")
def tv01(root):
    """Superseded by §9 (TL01): a tag-derived project is no longer refused; its label is the tag."""
    r = Repo(root, "tv01")
    r.write("pyproject.toml", '[build-system]\nrequires = ["setuptools", "setuptools_scm"]\n'
                              '[project]\nname = "pkg"\ndynamic = ["version"]\n')
    r.write("pkg/core.py", "x\n")
    r.commit()
    r.tag("v1")
    doc = expect(r, "inconclusive", 2, "--closure", "pkg/**")
    check(doc["label_sources"] == {"(the tag)": 1}, "label_sources = %r" % doc["label_sources"])


@proof("TV02")
def tv02(root):
    r = Repo(root, "tv02")
    r.write("src/a.py", "x\n")
    r.commit()
    r.tag("v1")
    rc, _, out, err = run(r)
    refusal(rc, out, err, "could not find a version label")
    check("derived from the tag" not in err, "the tag-derived cause was named without evidence")


# ---------------------------------------------------------------- TF — tag families

@proof("TF01")
def tf01(root):
    r = families(root, "tf01")
    doc = expect(r, "drift", 1)
    check(set(doc.get("tag_families", {})) == {"rs-", "py-"}, "tag_families = %r" % doc.get("tag_families"))
    _, _, out, _ = run(r, text=True)
    check("--tags" in out and "different prefixes" in out, "the text report does not suggest --tags")


@proof("TF02")
def tf02(root):
    r = two_tags(root, "tf02")
    doc = expect(r, "drift", 1)
    check("tag_families" not in doc, "tag_families reported for one family: %r" % doc.get("tag_families"))
    _, _, out, _ = run(r, text=True)
    check("different prefixes" not in out, "a suggestion was printed for one family")


# ---------------------------------------------------------------- EX — the excluded folders, at the root too

@proof("EX01")
def ex01(root):
    """Only files under a root-level tests/ and docs/, and a root README.md, change under one label."""
    r = Repo(root, "ex01")
    r.release("v1", "1.0.0", {"src/a.py": "same\n", "tests/test_a.py": "1\n", "docs/conf.py": "1\n", "README.md": "1\n"})
    r.release("v2", "1.0.0", {"tests/test_a.py": "2\n", "docs/conf.py": "2\n", "README.md": "2\n"})
    expect(r, "inconclusive", 2)


@proof("EX02")
def ex02(root):
    """The same folders one level down were already excluded, and still are."""
    r = Repo(root, "ex02")
    r.release("v1", "1.0.0", {"src/a.py": "same\n", "src/tests/test_a.py": "1\n", "pkg/docs/conf.py": "1\n"})
    r.release("v2", "1.0.0", {"src/tests/test_a.py": "2\n", "pkg/docs/conf.py": "2\n"})
    expect(r, "inconclusive", 2, "--closure", "src/**", "--closure", "pkg/**")


# ---------------------------------------------------------------- PT — the source is resolved at each point

def moving_source(root, name, labels=("1.0", "1.1", "1.2")):
    r = Repo(root, name)
    r.write("setup.py", 'from setuptools import setup\nsetup(name="pkg", version="%s")\n' % labels[0])
    r.write("pkg/core.py", "one\n")
    r.commit("t1"); r.tag("t1")
    r.write("setup.py", 'from setuptools import setup\nimport pkg\nsetup(name="pkg", version=pkg.__version__)\n')
    r.write("pkg/__init__.py", '__version__ = "%s"\n' % labels[1])
    r.write("pkg/core.py", "two\n")
    r.commit("t2"); r.tag("t2")
    r.remove("setup.py")
    r.write("pkg/__init__.py", "")
    r.write("pyproject.toml", '[project]\nname = "pkg"\nversion = "%s"\n' % labels[2])
    r.write("pkg/core.py", "three\n")
    r.commit("t3"); r.tag("t3")
    return r


@proof("PT01")
def pt01(root):
    doc = expect(moving_source(root, "pt01"), "clean", 0, "--closure", "pkg/core.py",
                 publication_points_compared=3, labels=3)
    check(set(doc["label_sources"]) == {"setup.py", "pkg/__init__.py", "pyproject.toml"},
          "label_sources = %r" % doc["label_sources"])


@proof("PT02")
def pt02(root):
    expect(moving_source(root, "pt02", ("1.0", "1.1", "1.0")), "drift", 1, "--closure", "pkg/core.py")


@proof("PT03")
def pt03(root):
    doc = expect(moving_source(root, "pt03"), "inconclusive", 2, "--closure", "pkg/core.py",
                 "--version-file", "pyproject.toml", publication_points_compared=1)
    check(doc["label_sources"] == {"pyproject.toml": 1}, "label_sources = %r" % doc["label_sources"])


# ---------------------------------------------------------------- TL — the label is the tag

def scm_repo(root, name, tags, comment_only=False):
    r = Repo(root, name)
    for i, tag in enumerate(tags):
        r.write("pyproject.toml", ('[build-system]\nrequires = ["setuptools"%s]\n[project]\nname = "pkg"\n'
                                   'dynamic = ["version"]\n%s')
                % ("" if comment_only else ', "setuptools_scm"',
                   "# we do not use setuptools_scm\n" if comment_only else ""))
        r.write("pkg/__init__.py", '__version__ = "%s"\n' % ("1.0" if comment_only else "unknown"))
        r.write("pkg/core.py", "state %d\n" % i)
        r.commit(tag); r.tag(tag)
    return r


@proof("TL01")
def tl01(root):
    doc = expect(scm_repo(root, "tl01", ["v1.0", "v1.1"]), "clean", 0, "--closure", "pkg/core.py", labels=2)
    check(doc["label_sources"] == {"(the tag)": 2}, "label_sources = %r" % doc["label_sources"])
    cmp_doc = expect(scm_repo(root, "tl01b", ["v1.0", "v1.1"]), "differs_under_two_labels", 0,
                     "--closure", "pkg/core.py", "--compare", "v1.0", "v1.1")
    check((cmp_doc["a"]["label"], cmp_doc["b"]["label"]) == ("1.0", "1.1"), "labels are not the tags without v")


@proof("TL02")
def tl02(root):
    doc = expect(scm_repo(root, "tl02", ["v1.0", "v1.1", "1.0"]), "drift", 1, "--closure", "pkg/core.py")
    check(list(doc["drift"]) == ["1.0"], "the label in drift is %r" % list(doc["drift"]))


@proof("TL03")
def tl03(root):
    rc, _, out, err = run(scm_repo(root, "tl03", ["v1.0", "v1.1"]), "--at", "commits")
    refusal(rc, out, err, "derived from the tag")


@proof("TL04")
def tl04(root):
    r = scm_repo(root, "tl04", ["v1.0", "v1.1"])
    expect(r, "no_label_at_head", 2, "--would-tag", "--closure", "pkg/core.py")
    _, _, out, _ = run(r, "--would-tag", "--closure", "pkg/core.py", text=True)
    check("the label will be" in out, "the text does not say the version will be the tag")


@proof("TL05")
def tl05(root):
    doc = expect(scm_repo(root, "tl05", ["v1.0", "v1.1"], comment_only=True), "drift", 1,
                 "--closure", "pkg/core.py")
    check(doc["label_sources"] == {"pkg/__init__.py": 2}, "label_sources = %r" % doc["label_sources"])


# ---------------------------------------------------------------- VP — declared pointers

def pointer_repo(root, name, files_for):
    """files_for(version) -> {path: text}; two tags, two versions, two closures."""
    r = Repo(root, name)
    for tag, version in (("t1", "2.0.0"), ("t2", "2.1.0")):
        for path, body in files_for(version).items():
            r.write(path, body)
        r.write("pkg/core.py", "code for %s\n" % version)
        r.commit(tag); r.tag(tag)
    return r


def pointer_proof(root, name, files_for, source):
    doc = expect(pointer_repo(root, name, files_for), "clean", 0, "--closure", "pkg/core.py", labels=2)
    check(doc["label_sources"] == {source: 2}, "label read from %r, required %r" % (doc["label_sources"], source))
    return doc


@proof("VP01")
def vp01(root):
    pointer_proof(root, "vp01", lambda v: {
        "pyproject.toml": '[build-system]\nrequires = ["hatchling"]\n[project]\nname = "pkg"\ndynamic = ["version"]\n'
                          '[tool.hatch.version]\npath = "pkg/_meta.py"\n',
        "pkg/_meta.py": 'VERSION = "%s"\n' % v}, "pkg/_meta.py")


@proof("VP02")
def vp02(root):
    pointer_proof(root, "vp02", lambda v: {
        "pyproject.toml": '[project]\nname = "pkg"\ndynamic = ["version"]\n[tool.setuptools.dynamic]\n'
                          'version = {attr = "pkg.__version__"}\n',
        "src/pkg/__init__.py": '__version__ = "%s"\n' % v, "pkg/core.py": ""}, "src/pkg/__init__.py")


@proof("VP03")
def vp03(root):
    pointer_proof(root, "vp03", lambda v: {
        "setup.cfg": "[metadata]\nname = pkg\nversion = attr: pkg.__version__\n",
        "pkg/__init__.py": '__version__ = "%s"\n' % v}, "pkg/__init__.py")


@proof("VP04")
def vp04(root):
    pointer_proof(root, "vp04a", lambda v: {
        "pyproject.toml": '[project]\nname = "pkg"\ndynamic = ["version"]\n[tool.setuptools.dynamic]\n'
                          'version = {file = "REL.txt"}\n', "REL.txt": v + "\n"}, "REL.txt")
    pointer_proof(root, "vp04b", lambda v: {
        "setup.cfg": "[metadata]\nname = pkg\nversion = file: REL.txt\n", "REL.txt": v + "\n"}, "REL.txt")


@proof("VP05")
def vp05(root):
    pointer_proof(root, "vp05", lambda v: {
        "pyproject.toml": '[build-system]\nrequires = ["flit_core"]\nbuild-backend = "flit_core.buildapi"\n'
                          '[project]\nname = "my-mod"\ndynamic = ["version"]\n',
        "my_mod.py": '"""doc"""\n__version__ = "%s"\n' % v}, "my_mod.py")


@proof("VP06")
def vp06(root):
    pointer_proof(root, "vp06", lambda v: {
        "setup.py": "import relinfo\nfrom setuptools import setup\nsetup(name='pkg', version=relinfo.RELEASE)\n",
        "tools/build/relinfo.py": 'RELEASE = "%s"\n' % v}, "tools/build/relinfo.py")


@proof("VP07")
def vp07(root):
    pointer_proof(root, "vp07", lambda v: {
        "setup.py": "from setuptools import setup\nVERSION = '%s'\nsetup(name='pkg', version=VERSION)\n" % v},
        "setup.py")


@proof("VP08")
def vp08(root):
    r = Repo(root, "vp08")
    for tag, version, vendored in (("t1", "2.0.0", "0.1"), ("t2", "2.1.0", "0.2")):
        r.write("setup.py", "from setuptools import setup\nsetup(name='pkg')\n")
        r.write("pkg/__init__.py", "from ._version import __version__\n")
        r.write("pkg/_version.py", '__version__ = "%s"\n' % version)
        r.write("pkg/io/extern/clip/__init__.py", '__version__ = "%s"\n' % vendored)
        r.write("pkg/core.py", "code for %s\n" % version)
        r.commit(tag); r.tag(tag)
    doc = expect(r, "clean", 0, "--closure", "pkg/core.py", labels=2)
    check(doc["label_sources"] == {"pkg/_version.py": 2}, "label read from %r" % doc["label_sources"])


@proof("VP09")
def vp09(root):
    r = Repo(root, "vp09")
    r.write("main.c", "int main(){}\n")
    r.commit(); r.tag("v1")
    rc, _, out, err = run(r, "--closure", "*.c")
    refusal(rc, out, err, "could not find a version label")


# ---------------------------------------------------------------- PL — a label must be a version

def two_versions(root, name, files_for, *args, verdict="clean", code=0, **fields):
    r = Repo(root, name)
    for tag, version in (("t1", "1.2.3"), ("t2", "1.2.4")):
        for path, body in files_for(version).items():
            r.write(path, body)
        r.write("pkg/core.py", "code for %s\n" % version)
        r.commit(tag); r.tag(tag)
    return expect(r, verdict, code, "--closure", "pkg/core.py", *args, **fields)


@proof("PL01")
def pl01(root):
    for n, bad in enumerate(("%(version)s", "{}.{}.{}", "%s", "unknown", ".", "0.0.0")):
        doc = two_versions(root, "pl01-%d" % n, lambda v: {
            "pyproject.toml": '[project]\nname = "pkg"\nversion = "%s"\n' % bad,
            "pkg/__init__.py": '__version__ = "%s"\n' % v}, labels=2)
        check(doc["label_sources"] == {"pkg/__init__.py": 2},
              "with %r in pyproject.toml the label came from %r" % (bad, doc["label_sources"]))


@proof("PL02")
def pl02(root):
    doc = two_versions(root, "pl02", lambda v: {
        "setup.py": "from setuptools import setup\nsetup(name='pkg')\n",
        "pkg/_version.py": "version_info = (1, 2)\n__version__ = '.'.join(map(str, version_info))\n",
        "pkg/__init__.py": '__version__ = "%s"\n' % v}, labels=2)
    check(doc["label_sources"] == {"pkg/__init__.py": 2}, "label read from %r" % doc["label_sources"])


@proof("PL03")
def pl03(root):
    doc = two_versions(root, "pl03", lambda v: {
        "setup.py": 'from ez_setup import use_setuptools\nuse_setuptools(version="0.6c5")\n'
                    'from setuptools import setup\nsetup(name="pkg", version="%s")\n' % v}, labels=2)
    check(doc["label_sources"] == {"setup.py": 2}, "label read from %r" % doc["label_sources"])


@proof("PL04")
def pl04(root):
    doc = two_versions(root, "pl04", lambda v: {
        "setup.py": 'print "building"\nfrom setuptools import setup\nsetup(name="pkg",\n      version="%s")\n' % v},
        labels=2)
    check(doc["label_sources"] == {"setup.py": 2}, "label read from %r" % doc["label_sources"])


@proof("PL05")
def pl05(root):
    doc = two_versions(root, "pl05", lambda v: {"REL": 'rel = "%(v)s-1"\n'},
                       "--version-file", "REL", "--version-regex", 'rel = "([^"]+)"', verdict="drift", code=1)
    check(list(doc["drift"]) == ["%(v)s-1"], "an explicit source was filtered: %r" % list(doc["drift"]))


# ---------------------------------------------------------------- K02 — the report is a contract

MEASURE_FIELDS = {"label_sources", "report_format", "stamp", "repo", "version_file", "closure_globs", "published_at",
                  "verdict", "labels", "labels_covering_multiple_closures", "max_closures_per_label",
                  "drift", "closure_ids", "closure_changes_between_points", "publication_points",
                  "publication_points_scanned", "publication_points_compared", "points_without_label",
                  "points_with_empty_closure", "points_not_commits", "range_truncated"}
WOULD_TAG_FIELDS = {"report_format", "stamp", "mode", "repo", "version_file", "closure_globs",
                    "published_at", "verdict", "label_at_head", "closure_at_head", "closure_id_at_head",
                    "collides_with", "existing_drift_labels", "publication_points_scanned",
                    "publication_points_compared", "points_without_label", "points_with_empty_closure",
                    "points_not_commits", "range_truncated"}
EXIT_OF = {"clean": 0, "would_be_clean": 0, "identical": 0, "differs_under_two_labels": 0,
           "drift": 1, "would_drift": 1, "differs_under_one_label": 1, "not_comparable": 2, "inconclusive": 2,
           "incomplete": 2, "no_labels": 2, "empty_closure": 2, "no_publication_points": 2,
           "no_label_at_head": 2, "empty_closure_at_head": 2}


@proof("K02")
def k02(root):
    """docs/REPORT.md: the fields each kind of report must carry, and the exit code of each verdict."""
    drifty, cleanly = two_tags(root, "k02a"), two_tags(root, "k02b", "1", "2")
    lone = Repo(root, "k02c")
    lone.write("package.json", '{"version":"1"}\n')
    lone.write("src/a.py", "x\n")
    lone.commit()
    runs = [(drifty, (), MEASURE_FIELDS), (cleanly, (), MEASURE_FIELDS),
            (cleanly, ("--closure", "nothing/**"), MEASURE_FIELDS),
            (two_tags(root, "k02d", same=True), (), MEASURE_FIELDS),
            (half_labelled(root, "k02e"), ("--version-file", "package.json", "--strict"), MEASURE_FIELDS),
            (drifty, ("--would-tag",), WOULD_TAG_FIELDS), (cleanly, ("--would-tag",), WOULD_TAG_FIELDS),
            (drifty, ("--compare", "v1", "v2"),
             {"report_format", "stamp", "mode", "repo", "version_file", "closure_globs", "verdict",
              "a", "b", "changed", "only_in_a", "only_in_b"}),
            (lone, (), {"report_format", "verdict", "note"})]
    seen = set()
    for repo, args, fields in runs:
        rc, doc, out, err = run(repo, *args)
        check(doc is not None, "no report for %s: %s" % (args, err[:120]))
        missing = fields - set(doc)
        check(not missing, "report %s lacks %s" % (doc.get("verdict"), sorted(missing)))
        check(doc["report_format"] == 2, "report_format = %r" % doc["report_format"])
        check(doc["verdict"] in EXIT_OF, "verdict outside the closed set: %r" % doc["verdict"])
        check(rc == EXIT_OF[doc["verdict"]], "verdict %s left at exit %d" % (doc["verdict"], rc))
        if "stamp" in fields:
            check({"measured_at_head", "working_tree_dirty", "detector_closure"} <= set(doc["stamp"]),
                  "the stamp is incomplete")
        seen.add(doc["verdict"])
    want = {"drift", "clean", "empty_closure", "inconclusive", "incomplete", "would_be_clean",
            "no_publication_points", "differs_under_one_label"}
    check(want <= seen, "the proof did not reach every kind of report: missing %s" % sorted(want - seen))
    rc, doc, out, err = run(root / "not-a-repository")
    check(rc == 2 and not out.strip() and err.strip(), "a refusal must leave standard output empty")


# ---------------------------------------------------------------- runner

def remove(path):
    def force(fn, p, _exc):
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        fn(p)
    shutil.rmtree(path, onerror=force)


# ---------------------------------------------------------------- §10 — the four open failures of 0.9.1

def labelled_and_not(root, name, labelled, unlabelled, empty=False):
    """`unlabelled` tags first (no version file, or no file in the closure), then `labelled` ones."""
    r = Repo(root, name)
    for i in range(unlabelled):
        r.write("README.txt" if empty else "src/a.py", "u%d\n" % i)
        r.commit()
        r.tag("v%d" % (i + 1))
    for j, (version, code) in enumerate(labelled):
        r.release("v%d" % (unlabelled + j + 1), version, {"src/a.py": code})
    return r


@proof("CV01")
def cv01(root):
    r = labelled_and_not(root, "cv01", [("4.0.0", "a\n"), ("5.0.0", "b\n")], 3)
    expect(r, "incomplete", 2, "--closure", "src/**", publication_points_compared=2, points_without_label=3)


@proof("CV02")
def cv02(root):
    r = labelled_and_not(root, "cv02", [("4.0.0", "a\n"), ("5.0.0", "b\n"), ("6.0.0", "c\n")], 3)
    expect(r, "clean", 0, "--closure", "src/**", publication_points_compared=3, points_without_label=3)


@proof("CV03")
def cv03(root):
    r = labelled_and_not(root, "cv03", [("6.0.0", "a\n"), ("6.0.0", "b\n")], 5)
    expect(r, "drift", 1, "--closure", "src/**", publication_points_compared=2)


@proof("CV04")
def cv04(root):
    r = labelled_and_not(root, "cv04", [("4.0.0", "a\n"), ("5.0.0", "b\n")], 3, empty=True)
    expect(r, "incomplete", 2, "--closure", "src/**", points_with_empty_closure=3)


@proof("CV05")
def cv05(root):
    r = labelled_and_not(root, "cv05", [("4.0.0", "a\n"), ("5.0.0", "b\n")], 3)
    rc, _, out, _ = run(r, "--closure", "src/**", text=True)
    check(rc == 2, "exit %d" % rc)
    check("at least as many compared as not" in out, "the text does not name the rule")
    check("over the 2 points compared" in out and "3 could not be compared" in out, "the text does not give the counts")


def cargo_history(root, name, tags, version="0.1.0", head=False):
    r = Repo(root, name)
    for i, tag in enumerate(tags):
        r.write("Cargo.toml", '[package]\nname = "helper"\nversion = "%s"\n' % version)
        r.write("src/a.rs", "// %d\n" % i)
        r.commit()
        r.tag(tag)
    if head:
        r.write("src/a.rs", "// head\n")
        r.commit()
    return r


@proof("AG01")
def ag01(root):
    expect(cargo_history(root, "ag01", ["v2.1.0", "v2.2.0"]), "incomplete", 2,
           points_label_contradicted=2, contradicted_sources=["Cargo.toml"], publication_points_compared=0,
           points_without_label=2)


@proof("AG02")
def ag02(root):
    r = Repo(root, "ag02")
    for tag, version in (("v1.0", "1.0.0"), ("v1.1", "1.1.0")):
        r.write("pyproject.toml", '[project]\nname = "pkg"\nversion = "%s"\n' % version)
        r.write("pkg/a.py", "# %s\n" % version)
        r.commit()
        r.tag(tag)
    expect(r, "clean", 0, labels=2, points_label_contradicted=0)


@proof("AG03")
def ag03(root):
    r = Repo(root, "ag03")
    for tag, version in (("v1.0.0", "1.0.0"), ("v1.1.0", "1.1.0"), ("v1.2.0", "1.1.0")):
        r.release(tag, version, {"src/a.py": "# %s\n" % tag})
    expect(r, "drift", 1, points_label_contradicted=0)


@proof("AG04")
def ag04(root):
    expect(cargo_history(root, "ag04", ["v2.1.0", "v2.2.0"]), "drift", 1, "--version-file", "Cargo.toml",
           points_label_contradicted=0)


@proof("AG05")
def ag05(root):
    expect(cargo_history(root, "ag05", ["nightly", "stable"]), "drift", 1, points_label_contradicted=0)


@proof("AG06")
def ag06(root):
    doc = expect(cargo_history(root, "ag06", ["v2.1.0", "v2.2.0"], head=True), "no_label_at_head", 2,
                 "--would-tag")
    check(doc.get("label_at_head_rejected") == {"label": "0.1.0", "source": "Cargo.toml"},
          "the rejected label is not named: %r" % doc.get("label_at_head_rejected"))


@proof("AG07")
def ag07(root):
    r = Repo(root, "ag07")
    for tag, version in (("v2.52.0-rc0", "2.52.0"), ("v2.53.0", "2.53.0")):
        r.release(tag, version, {"src/a.py": "# %s\n" % tag})
    expect(r, "clean", 0, points_label_contradicted=0)


MAKEFILE = "VERSION = 6\nPATCHLEVEL = 1\nSUBLEVEL = 0\nEXTRAVERSION =%s\n"
NAMED = r"(?m)^VERSION = (?P<part1>\d+)\nPATCHLEVEL = (?P<part2>\d+)\nSUBLEVEL = (?P<part3>\d+)"


def label_at_head(root, name, makefile, pattern):
    r = Repo(root, name)
    r.write("Makefile", makefile)
    r.write("src/a.c", "int a;\n")
    r.commit()
    r.tag("v5.0")
    r.write("src/a.c", "int b;\n")
    r.commit()
    _rc, doc, out, err = run(r, "--would-tag", "--version-file", "Makefile", "--version-regex", pattern)
    check(doc is not None, "no report: %s" % err[:160])
    return doc["label_at_head"]


@proof("NG01")
def ng01(root):
    got = label_at_head(root, "ng01", MAKEFILE % "", NAMED)
    check(got == "6.1.0", "label %r" % got)


@proof("NG02")
def ng02(root):
    got = label_at_head(root, "ng02", MAKEFILE % " -rc1", NAMED + r"\nEXTRAVERSION =[ \t]*(?P<part4>\S*)")
    check(got == "6.1.0-rc1", "label %r" % got)


@proof("NG03")
def ng03(root):
    got = label_at_head(root, "ng03", MAKEFILE % "", NAMED + r"\nEXTRAVERSION =[ \t]*(?P<part4>\S*)")
    check(got == "6.1.0", "label %r" % got)


@proof("NG04")
def ng04(root):
    got = label_at_head(root, "ng04", 'version = "6.1"\n', r'version = "(\d+)\.(\d+)"')
    check(got == "6", "label %r" % got)


@proof("NG05")
def ng05(root):
    r = Repo(root, "ng05")
    r.write("src/a.c", "int a;\n")
    r.commit()
    r.tag("v1")
    rc, _, out, err = run(r, text=True)
    refusal(rc, out, err, "--version-file")
    for needle in ("(?P<part1>", "docs/LABELS.md", "version is the tag"):
        check(needle in err, "the refusal does not mention %r" % needle)


@proof("AG08")
def ag08(root):
    r = Repo(root, "ag08")
    for tag, version in (("v1.0", "1.0"), ("v1.1", "1.1"), ("v1.2", "1.2")):
        r.write("setup.py", 'from setuptools import setup\nsetup(name="pkg", version="%s")\n' % version)
        r.write("pkg/a.py", "# %s\n" % tag)
        r.commit()
        r.tag(tag)
    r.remove("setup.py")
    for tag in ("2024.1", "2024.2"):
        r.write("pyproject.toml", '[project]\nname = "pkg"\nversion = "5.0.0"\n')
        r.write("pkg/a.py", "# %s\n" % tag)
        r.commit()
        r.tag(tag)
    rc, doc, _out, err = run(r)
    check(doc is not None and rc != 0 and doc.get("verdict") != "clean",
          "a collision under a contradicted source ended at %r, exit %d" % (doc and doc.get("verdict"), rc))


@proof("AG09")
def ag09(root):
    r = Repo(root, "ag09")
    for tag in ("v1.1", "v1.2", "v1.3"):
        r.release(tag, "1.0.0", {"src/a.py": "# %s\n" % tag})
    expect(r, "drift", 1, points_label_contradicted=0)


@proof("AG10")
def ag10(root):
    r = Repo(root, "ag10")
    for tag in ("0.1.450", "0.1.451"):
        r.write("package.json", '{"private": true, "name": "x", "version": "0.0.3"}\n')
        r.write("src/a.js", "// %s\n" % tag)
        r.commit()
        r.tag(tag)
    rc, _doc, out, err = run(r)
    check(rc == 2, "exit %d: a private package.json was read as the version" % rc)


@proof("AG11")
def ag11(root):
    r = Repo(root, "ag11")
    for tag, line in (("v1", 'version = "1.0"\n'), ("v2", "version = '1.0'\n")):
        r.write("ver.cfg", line)
        r.write("src/a.py", "# %s\n" % tag)
        r.commit()
        r.tag(tag)
    rc, doc, _out, err = run(r, "--version-file", "ver.cfg", "--version-regex", "version = ([\"'])")
    check(rc != 0, "a pattern capturing a quote gave %r, exit 0" % (doc and doc.get("verdict")))


@proof("AG12")
def ag12(root):
    r = Repo(root, "ag12")
    for tag, version in (("v1.0", "0.9.0"), ("v1.1", "1.0.0"), ("v1.1.1", "1.0.0")):
        r.release(tag, version, {"src/a.py": "# %s\n" % tag})
    expect(r, "drift", 1, points_label_contradicted=0)


def many_trees(root, name, n=8):
    r = Repo(root, name)
    for i in range(n):
        r.release("v%d.0.0" % (i + 1), "%d.0.0" % (i + 1), {"src/m%d/a%d.py" % (i % 7, i): "%d\n" % i})
    return r


@proof("MM01")
def mm01(root):
    r = many_trees(root, "mm01")
    _rc, _d, plain, _e = run(r, "--max-commits", "1000")
    _rc, _d, small, _e = run(r, "--max-commits", "1000", env=dict(ENV, CLOSURE_DRIFT_TREE_CACHE="50"))
    check(plain == small, "the report changed with the cache bounded at 50 entries")


@proof("MM02")
def mm02(root):
    r = many_trees(root, "mm02")
    _rc, _d, plain, _e = run(r, "--max-commits", "1000")
    _rc, _d, small, _e = run(r, "--max-commits", "1000", env=dict(ENV, CLOSURE_DRIFT_TREE_CACHE="1"))
    check(plain == small, "the report changed with the cache bounded at 1 entry")


@proof("MM03")
def mm03(root):
    r = many_trees(root, "mm03")
    os.environ["CLOSURE_DRIFT_TREE_CACHE"] = "50"
    try:
        module = load_detector()
        objects = module.Objects(str(r.path))
        largest = 0
        try:
            for sha in r.git("rev-list", "--all").split():
                for _p, _k, _o in objects.entries(sha):
                    pass
                largest = max([largest] + [len(v) + 1 for v in objects.trees.values()])
                held = sum(len(v) + 1 for v in objects.trees.values())
                check(held <= 50 + largest, "the cache holds %d entries over a bound of 50" % held)
                check(held == objects.held, "the cache counts %d entries and holds %d" % (objects.held, held))
        finally:
            objects.close()
    finally:
        del os.environ["CLOSURE_DRIFT_TREE_CACHE"]


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
