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
    starts = [l.strip() for l in src.splitlines()
              if ("subprocess.run(" in l or "subprocess.Popen(" in l) and not l.strip().startswith("#")]
    allowed_starts = ("[*GIT,", "[sys.executable, os.path.abspath(__file__), \"--match-on-stdin\"]")
    stray = [l for l in starts if not any(a in l for a in allowed_starts)]
    check(len(starts) == 3 and not stray,
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
