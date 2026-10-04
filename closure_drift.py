#!/usr/bin/env python3
"""closure_drift — does your version label name exactly one version of your code?

Read-only, no dependencies. At each publication point (a tag, by default) it reads the declared
version and hashes the files that determine your output; a version that covers two different
hashes is drift.

  closure_drift.py                              # drift at tags
  closure_drift.py --would-tag                  # before you tag: would this commit reuse a label?
  closure_drift.py --tags 'v*'                  # only these tags are publication points
  closure_drift.py --at commits                 # you publish at every commit
  closure_drift.py --closure 'src/**/*.py'      # what determines your output
  closure_drift.py --strict | --explain LABEL | --compare A B | --diagnose | --json | --badge

Exit codes: 0 clean · 1 drift · 2 no determination (cause named). Nothing else ends at 0, no
input produces a traceback, and no failure ends at 1.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import unicodedata
import warnings
from collections import defaultdict
from pathlib import Path

__version__ = "0.9.0"
REPORT_FORMAT = 2

# Where a version can be declared. Python build files are read first; a repository that has
# them is a Python project, and only then are the other ecosystems' files consulted.
BUILD_FILES = ("pyproject.toml", "setup.cfg", "setup.py")
OTHER_ECOSYSTEMS = (("Cargo.toml", "cargo"), ("package.json", "json"), ("composer.json", "json"),
                    ("build.gradle", "gradle"), ("VERSION", "token"), ("version.txt", "token"))
VERSION_MODULES = ("__version__.py", "_version.py", "version.py", "__about__.py", "__init__.py")
VERSION_NAMES = ("__version__", "VERSION", "version")
TAG_SOURCE = "(the tag)"      # the version is derived from the tag at build time: the label is the tag
DEFAULT_VERSION_REGEX = r'(?<![\w-])"?version"?\s*[:=]\s*["\']([^"\']+)["\']'
BUILT_IN_PATTERNS = {DEFAULT_VERSION_REGEX}

# Build tools that take the version from the tag. They count only where the build declares them.
SCM_TOOLS = {"setuptools-scm", "hatch-vcs", "versioneer", "versioningit", "poetry-dynamic-versioning",
             "setuptools-git-versioning", "dunamai", "pbr"}
SCM_TABLES = {"tool.setuptools_scm", "tool.versioneer", "tool.versioningit", "tool.setuptools-git-versioning"}
NOT_PACKAGES = {"src", "lib", "tests", "test", "docs", "doc", "examples", "example", "scripts", "tools",
                "benchmarks", "bench", "extern", "vendor", "_vendor", "third_party", "build", "dist"}
PLACEHOLDERS = {"0.0.0", "0.0.0.dev0", "0+unknown"}
MAX_BUILD_FILE = 1 << 20      # a build file larger than this is not read for a version

DIAGNOSTICS: dict = {}     # filled only with --diagnose; added to every JSON report

CLOSURE_DEFAULTS = ["src/**", "lib/**", "app/**", "*.py", "*.js", "*.ts", "*.rs", "*.go", "*.java"]

# never part of a closure: churn that cannot change behaviour
CLOSURE_EXCLUDE = ["**/test/**", "**/tests/**", "**/*_test.*", "**/*.test.*", "**/spec/**",
                   "**/docs/**", "**/*.md", "**/node_modules/**", "**/vendor/**", "**/.git/**"]

# Seconds a user-supplied version pattern may spend on one file.
REGEX_BUDGET = 5


class Refusal(Exception):
    """A named reason why no measurement was produced. Always exit 2, never a traceback."""


# Every git call uses these. They stop git from running commands named in the measured
# repository's config (fsmonitor, lazy fetch), from writing to it (optional locks), and from
# reading a different object than the one named (replace refs).
GIT = ["git", "--no-optional-locks", "--no-replace-objects", "-c", "core.fsmonitor=false"]

# Variables that would make git read another repository than the one named. Removed, not obeyed.
REDIRECTING = ("GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
               "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_NAMESPACE", "GIT_GRAFT_FILE",
               "GIT_SHALLOW_FILE", "GIT_REPLACE_REF_BASE", "GIT_CONFIG")


def git_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in REDIRECTING}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", GIT_NO_REPLACE_OBJECTS="1",
               GIT_NO_LAZY_FETCH="1", LC_ALL="C")
    return env


def git_bytes(args: list[str], repo: str, may_fail: bool = False) -> bytes | None:
    """Output of a git command. A failure is a Refusal, or None when may_fail — never empty output."""
    try:
        r = subprocess.run([*GIT, "-C", repo, *args], capture_output=True, env=git_env())
    except OSError as e:
        raise Refusal(f"cannot run git: {e.strerror or e}")
    if r.returncode != 0:
        if may_fail:
            return None
        first = (r.stderr.decode("utf-8", "replace").strip().splitlines() or ["no message"])[0]
        raise Refusal(f"git {args[0]} failed (exit {r.returncode}): {printable(first[:200])}")
    return r.stdout


def git(args: list[str], repo: str, may_fail: bool = False) -> str:
    out = git_bytes(args, repo, may_fail)
    return "" if out is None else out.decode("utf-8", "replace")


def emit(report: dict) -> None:
    if DIAGNOSTICS:
        report["diagnostics"] = DIAGNOSTICS
    print(json.dumps(report, indent=1))


def printable(text) -> str:
    """Text safe to print: control, format and invisible characters are written as escapes."""
    out = []
    for ch in str(text):
        o = ord(ch)
        cat = unicodedata.category(ch)
        if (o < 32 or 127 <= o < 160 or cat in ("Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp")
                or (cat == "Zs" and ch != " ")):
            out.append("\\x%02x" % o if o < 256 else "\\u%04x" % o)
        else:
            out.append(ch)
    return "".join(out)


def matches(path: str, globs: list[str]) -> bool:
    """`*` crosses folders; a leading `**/` matches zero or more of them."""
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path, g.replace("**/", "*/"))
               or (g.startswith("**/") and fnmatch.fnmatch(path, g[3:]))
               or (g.endswith("/**") and path.startswith(g[:-3] + "/")) for g in globs)


def check_globs(globs: list[str], what: str) -> None:
    """Refuse, by name, a glob that cannot be compiled."""
    for g in globs:
        for form in (g, g.replace("**/", "*/")):
            try:
                re.compile(fnmatch.translate(form))
            except (re.error, RecursionError, OverflowError) as e:
                raise Refusal(f"invalid {what} glob {g!r}: {e}")


def git_version() -> tuple[int, int]:
    try:
        r = subprocess.run([*GIT, "--version"], capture_output=True, env=git_env())
    except OSError as e:
        raise Refusal(f"cannot run git: {e.strerror or e}")
    m = re.search(r"(\d+)\.(\d+)", r.stdout.decode("utf-8", "replace"))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def local_config(repo: str) -> list[tuple[str, str]] | None:
    """[(key, value)] of the repository's own git config, or None when it cannot be read."""
    raw = git_bytes(["config", "--local", "--list", "-z"], repo, may_fail=True)
    if raw is None:
        return None
    out = []
    for item in raw.decode("utf-8", "replace").split("\0"):
        if item:
            key, _, value = item.partition("\n")
            out.append((key.lower(), value))
    return out


class Objects:
    """One `git cat-file --batch` for the whole run. Each tree object and each version file is
    read once; paths come from the objects themselves, so none is ever quoted."""

    def __init__(self, repo: str):
        self.repo = repo
        try:
            self.proc = subprocess.Popen([*GIT, "-C", repo, "cat-file", "--batch"], env=git_env(),
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.DEVNULL)
        except OSError as e:
            raise Refusal(f"cannot run git: {e.strerror or e}")
        self.trees: dict[str, list[tuple[bytes, str, str]]] = {}
        self.texts: dict[str, str] = {}

    def close(self) -> None:
        try:
            self.proc.stdin.close()
            self.proc.stdout.close()
            self.proc.wait(timeout=10)
        except Exception:  # noqa: BLE001 — closing is best effort; the measurement is already done
            self.proc.kill()

    def read(self, name: str, want: str) -> bytes:
        """The bytes of object `name`, which must be of type `want`."""
        try:
            self.proc.stdin.write(name.encode() + b"\n")
            self.proc.stdin.flush()
            header = self.proc.stdout.readline().split()
            if len(header) != 3 or header[1].decode() != want:
                said = b" ".join(header[1:]).decode("utf-8", "replace") or "no answer"
                raise Refusal(f"git cat-file could not read {want} {printable(name[:60])}: {printable(said)}")
            size = int(header[2])
            data = self.proc.stdout.read(size + 1)[:-1]
        except (OSError, ValueError) as e:
            raise Refusal(f"git cat-file failed while reading {printable(name[:60])}: {type(e).__name__}")
        if len(data) != size:
            raise Refusal(f"git cat-file returned a truncated {want} {printable(name[:60])}")
        return data

    def root_tree(self, commit: str) -> str:
        head = self.read(commit, "commit").split(b"\n", 1)[0]
        if not head.startswith(b"tree "):
            raise Refusal(f"commit {commit[:12]} names no tree")
        return head[5:].decode()

    def children(self, tree_oid: str) -> list[tuple[bytes, str, str]]:
        """[(name, kind, object id)] of one tree object, in git's own order."""
        got = self.trees.get(tree_oid)
        if got is not None:
            return got
        raw, width, out, i = self.read(tree_oid, "tree"), len(tree_oid) // 2, [], 0
        try:
            while i < len(raw):
                space = raw.index(b" ", i)
                nul = raw.index(b"\0", space)
                mode, name = raw[i:space], raw[space + 1:nul]
                end = nul + 1 + width
                if end > len(raw) or not name or b"/" in name or not mode.isdigit() or len(mode) > 6:
                    raise ValueError("entry out of shape")
                oid = raw[nul + 1:end].hex()
                i = end
                kind = "tree" if mode in (b"40000", b"040000") else "commit" if mode == b"160000" else "blob"
                out.append((name, kind, oid))
        except ValueError:
            raise Refusal(f"git returned a malformed tree object {tree_oid[:12]}: no measurement was produced")
        self.trees[tree_oid] = out
        return out

    def entries(self, commit: str) -> list[tuple[str, str, str]]:
        """[(path, kind, object id)] for every file and submodule pointer at a commit — the
        order and content of `git ls-tree -r -z`."""
        out: list[tuple[str, str, str]] = []
        stack = [(b"", self.root_tree(commit), 0)]
        while stack:
            prefix, tree_oid, start = stack.pop()
            kids = self.children(tree_oid)
            for n in range(start, len(kids)):
                name, kind, oid = kids[n]
                if kind == "tree":
                    stack.append((prefix, tree_oid, n + 1))
                    stack.append((prefix + name + b"/", oid, 0))
                    break
                out.append(((prefix + name).decode("utf-8", "surrogateescape"), kind, oid))
        return out

    def text(self, oid: str) -> str:
        if oid not in self.texts:
            self.texts[oid] = self.read(oid, "blob").decode("utf-8", errors="replace")
        return self.texts[oid]


class Closure:
    """Decides, once per distinct path, whether it is in the closure — and computes both ids."""

    def __init__(self, include: list[str]):
        self.include = include
        self.known: dict[str, bool] = {}

    def holds(self, path: str) -> bool:
        got = self.known.get(path)
        if got is None:
            got = matches(path, self.include) and not matches(path, CLOSURE_EXCLUDE)
            self.known[path] = got
        return got

    def members(self, entries: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
        return [e for e in entries if e[1] in ("blob", "commit") and self.holds(e[0])]

    def ids(self, entries: list[tuple[str, str, str]]) -> tuple[str, str, int]:
        """(short id, full id, number of files). The short id is the 16-hex value of every version
        since 0.3.0, kept for comparability; it joins path and object id with nothing between
        them, so identity is decided by the full id, over `path NUL type SP id LF`. Submodule
        pointers are part of the closure."""
        short, full, n = hashlib.sha256(), hashlib.sha256(), 0
        for path, kind, oid in self.members(entries):
            raw = path.encode("utf-8", "surrogateescape")
            short.update(raw)
            short.update(oid.encode())
            full.update(raw + b"\0" + kind.encode() + b" " + oid.encode() + b"\n")
            n += 1
        return short.hexdigest()[:16], full.hexdigest(), n


def closure_hash(entries: list[tuple[str, str, str]], include: list[str]) -> tuple[str, int]:
    """The 16-hex closure of 0.3.0 onward and the number of files in it. Kept under its historical
    name for anything that compares against published values; identity is Closure.ids()."""
    short, _full, n = Closure(include).ids(entries)
    return short, n


def bounded_search(pattern: str, text: str) -> str | None:
    """The label a pattern captures, or None. A pattern that is not built in is matched in a child
    process of this file under a time limit: it could be written never to finish."""
    if pattern in BUILT_IN_PATTERNS:
        m = re.search(pattern, text, re.MULTILINE)
        return m.group(1) if m else None
    try:
        r = subprocess.run([sys.executable, os.path.abspath(__file__), "--match-on-stdin"],
                           input=json.dumps({"pattern": pattern, "text": text}).encode("utf-8"),
                           capture_output=True, timeout=REGEX_BUDGET)
        return json.loads(r.stdout.decode("utf-8"))["label"]
    except subprocess.TimeoutExpired:
        raise Refusal(f"the version pattern {pattern!r} did not finish within {REGEX_BUDGET} seconds "
                      "on a version file. No measurement was produced.")
    except (OSError, ValueError, KeyError):
        raise Refusal(f"the version pattern {pattern!r} could not be evaluated")


def match_on_stdin() -> int:
    """The child side of bounded_search. Reads {"pattern", "text"}, prints {"label"}."""
    job = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    m = re.search(job["pattern"], job["text"], re.MULTILINE)
    sys.stdout.write(json.dumps({"label": m.group(1) if m else None}))
    return 0


def plausible(label) -> bool:
    """A label is a version someone wrote: it has a digit, and it is not a format template
    (`%(version)s`, `{}.{}`) nor a placeholder."""
    return (isinstance(label, str) and any(c.isdigit() for c in label)
            and not any(c in label for c in "%{}") and label not in PLACEHOLDERS)


_KEY = re.compile(r'^([A-Za-z_][\w.-]*)[ \t]*=[ \t]*(.*)$')
_STRING = re.compile(r'^(["\'])([^"\'\n]*)\1[ \t]*(?:[#;].*)?$')


def tables(text: str) -> dict:
    """{table: {key: right-hand side}} of a TOML or INI file. Read line by line, so the cost is
    linear in the size of the file whatever the file holds."""
    out: dict = {"": {}}
    table, last, open_array = "", None, 0
    for raw in text.split("\n"):
        line = raw.strip()
        if open_array:
            out[table][last] += " " + line
            open_array = 0 if "]" in line or open_array > 200 else open_array + 1
            continue
        if not line or line[0] in "#;":
            continue
        if line[0] == "[":
            table = line.split("#", 1)[0].strip().strip("[]").strip().strip("\"'")
            out.setdefault(table, {})
            last = None
            continue
        m = _KEY.match(line)
        if m and not (raw[:1] in " \t" and last and not m.group(2)):
            last = m.group(1)
            out[table].setdefault(last, m.group(2).strip())
            if out[table][last].startswith("[") and "]" not in out[table][last]:
                open_array = 1
        elif raw[:1] in " \t" and last:
            out[table][last] += " " + line          # an INI continuation line
    return out


def string(rhs) -> str | None:
    m = _STRING.match(rhs or "")
    return m.group(2) if m else None


def requirement(spec: str) -> str:
    m = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", spec.strip())
    return re.sub(r"[._]", "-", m.group(0).lower()) if m else ""


def attribute_value(text: str, name: str) -> str | None:
    """`name = "..."` at the start of a line, the string being the whole right-hand side."""
    tail = re.compile(r'[ \t]*(?::[^=\n]*)?=[ \t]*(["\'])([^"\'\n]*)\1[ \t]*(?:#.*)?$')
    for line in text.split("\n"):
        if line.startswith(name):
            m = tail.match(line, len(name))
            if m:
                return m.group(2)
    return None


def setup_info(text: str) -> dict:
    """What `setup(...)` in a setup.py says about the version — parsed, never executed. A
    setup.py that is not valid Python 3 is read from the text after `setup(`."""
    info = {"version": None, "module": None, "name": None, "scm": False}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError, MemoryError, OverflowError):
        body = "\n".join(l.split("#", 1)[0] for l in text[max(text.find("setup("), 0):].split("\n")) \
            if "setup(" in text else ""
        for key in ("version", "name"):
            m = re.search(r'(?:^|[(,])[ \t]*' + key + r'[ \t]*=[ \t]*["\']([^"\'\n]+)["\']', body, re.M)
            info[key] = m.group(1) if m else None
        info["scm"] = "use_scm_version" in body
        return info
    consts = {n.targets[0].id: n.value.value for n in tree.body
              if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
              and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        called = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
        if called != "setup":
            continue
        for kw in node.keywords:
            v = kw.value
            text_value = (v.value if isinstance(v, ast.Constant) and isinstance(v.value, str)
                          else consts.get(v.id) if isinstance(v, ast.Name) else None)
            if kw.arg == "version":
                info["version"] = text_value
                if isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name):
                    info["module"] = (v.value.id, v.attr)
                elif isinstance(v, ast.Call) and "versioneer" in ast.dump(v.func):
                    info["scm"] = True
            elif kw.arg == "name":
                info["name"] = text_value
            elif kw.arg in ("use_scm_version", "pbr") and not (isinstance(v, ast.Constant) and not v.value):
                info["scm"] = True
        break
    return info


def depth_first(paths) -> list[str]:
    return sorted(paths, key=lambda p: (p.count("/"), p))


class Sources:
    """Where the version label is, at one commit. Resolved at every publication point, with no
    memory of the other points: a project moves its version from setup.py to a module to
    pyproject.toml over the years, and the answer for a tag must not depend on which tag was
    looked at before it.

    For a Python project, in order: a pointer the build files declare; a tool the build declares
    that derives the version from the tag (then the label IS the tag); a version written in the
    build files; the version module of the project's own package. Otherwise the version file of
    another ecosystem."""

    def __init__(self, objects: Objects):
        self.objects = objects
        self.values: dict = {}        # (object id, how) -> label; a pure function of the bytes
        self.parsed: dict = {}

    def text(self, blobs: dict, path: str) -> str:
        oid = blobs.get(path)
        if oid is None:
            return ""
        text = self.objects.text(oid)
        return text if len(text) <= MAX_BUILD_FILE else ""

    def tables(self, blobs: dict, path: str) -> dict:
        oid = blobs.get(path)
        if (oid, "tables") not in self.parsed:
            self.parsed[(oid, "tables")] = tables(self.text(blobs, path))
        return self.parsed[(oid, "tables")]

    def setup(self, blobs: dict) -> dict:
        oid = blobs.get("setup.py")
        if (oid, "setup") not in self.parsed:
            self.parsed[(oid, "setup")] = setup_info(self.text(blobs, "setup.py"))
        return self.parsed[(oid, "setup")]

    def read(self, blobs: dict, path: str, how) -> str | None:
        """The label a source gives at this commit, or None when it gives no plausible one."""
        oid = blobs.get(path)
        if oid is None:
            return None
        if (oid, how) in self.values:
            return self.values[(oid, how)]
        text, value = self.text(blobs, path), None
        if how == "project":
            t = tables(text)
            value = string(t.get("project", {}).get("version")) or string(t.get("tool.poetry", {}).get("version"))
        elif how == "cargo":
            t = tables(text)
            value = string(t.get("package", {}).get("version")) or string(t.get("workspace.package", {}).get("version"))
        elif how == "cfg":
            value = tables(text).get("metadata", {}).get("version")
        elif how == "setup":
            value = setup_info(text)["version"]
        elif how == "json":
            try:
                doc = json.loads(text, strict=False)
                value = doc.get("version") if isinstance(doc, dict) else None
            except (ValueError, RecursionError):
                value = None
        elif how == "token":
            value = text.strip() if len(text.split()) == 1 else None
        elif how == "gradle":
            for line in text.split("\n"):
                m = re.match(r'[ \t]*version[ \t]*=?[ \t]*["\']([^"\'\n]+)["\']', line)
                if m:
                    value = m.group(1)
                    break
        else:
            value = attribute_value(text, how[1])
        self.values[(oid, how)] = value if plausible(value) else None
        return self.values[(oid, how)]

    def find(self, blobs: dict):
        """(path, how), (TAG_SOURCE, None), or None."""
        if any(n in blobs for n in BUILD_FILES):
            return self.python(blobs)
        for path, how in OTHER_ECOSYSTEMS:
            if self.read(blobs, path, how):
                return path, how
        return None

    def python(self, blobs: dict):
        pp, cfg, setup = self.tables(blobs, "pyproject.toml"), self.tables(blobs, "setup.cfg"), self.setup(blobs)
        project, hatch = pp.get("project", {}), pp.get("tool.hatch.version", {})
        metadata, build = cfg.get("metadata", {}), pp.get("build-system", {})
        name = (string(project.get("name")) or string(pp.get("tool.poetry", {}).get("name"))
                or metadata.get("name") or setup["name"])
        backend = string(build.get("build-backend")) or ""
        requires = {requirement(q) for q in re.findall(r'["\']([^"\'\n]*)["\']', build.get("requires", ""))}
        dynamic = "version" in project.get("dynamic", "")

        # 1. a pointer the build files declare
        if string(hatch.get("path")):
            for attr in VERSION_NAMES:
                if self.read(blobs, string(hatch.get("path")), ("attr", attr)):
                    return string(hatch.get("path")), ("attr", attr)
        for rhs in (pp.get("tool.setuptools.dynamic", {}).get("version", ""), metadata.get("version", "")):
            m = re.match(r'\{?[ \t]*attr[ \t]*[=:][ \t]*["\']?([A-Za-z_][\w.]*\.[A-Za-z_]\w*)', rhs)
            if m:
                got = self.attribute(blobs, m.group(1).split(".")[:-1], m.group(1).split(".")[-1])
                if got:
                    return got
            m = re.match(r'\{?[ \t]*file[ \t]*[=:][ \t]*\[?[ \t]*["\']?([^"\'\],}\s]+)', rhs)
            if m and self.read(blobs, m.group(1), "token"):
                return m.group(1), "token"
        if "maturin" in backend and dynamic and self.read(blobs, "Cargo.toml", "cargo"):
            return "Cargo.toml", "cargo"
        if "flit" in backend and name:
            got = self.attribute(blobs, [name.replace("-", "_")], "__version__")
            if got:
                return got

        # 2. the build declares a tool that derives the version from the tag
        if (set(pp) & SCM_TABLES or string(hatch.get("source")) == "vcs"
                or pp.get("tool.poetry-dynamic-versioning", {}).get("enable", "").startswith("true")
                or string(pp.get("tool.pdm.version", {}).get("source")) == "scm"
                or (requires & SCM_TOOLS and not string(project.get("version")))
                or setup["scm"] or "versioneer" in cfg or "pbr" in cfg):
            return TAG_SOURCE, None

        # 3. a version written in the build files
        if self.read(blobs, "pyproject.toml", "project"):
            return "pyproject.toml", "project"
        if not metadata.get("version", "").startswith(("attr", "file")) and self.read(blobs, "setup.cfg", "cfg"):
            return "setup.cfg", "cfg"
        if self.read(blobs, "setup.py", "setup"):
            return "setup.py", "setup"
        if setup["module"]:
            got = self.attribute(blobs, [setup["module"][0]], setup["module"][1], anywhere=True)
            if got:
                return got

        # 4. the version module of the project's own package
        for package in self.packages(blobs, name):
            for module in VERSION_MODULES:
                for attr in (("__version__",) if module == "__init__.py" else VERSION_NAMES):
                    if self.read(blobs, package + "/" + module, ("attr", attr)):
                        return package + "/" + module, ("attr", attr)
        return None

    def packages(self, blobs: dict, name: str | None) -> list[str]:
        """The folders of the package this project builds: the one its name says, or the only
        top-level package there is. Not a vendored one, not a tests folder."""
        if name:
            n = name.replace("-", "_").replace(".", "/")
            named = [base + c for c in dict.fromkeys((n, n.lower())) for base in ("", "src/", "lib/")
                     if base + c + "/__init__.py" in blobs]
            if named:
                return named
        tops = set()
        for p in blobs:
            parts = p.split("/")
            if parts[-1] != "__init__.py":
                continue
            if len(parts) == 2 and parts[0] not in NOT_PACKAGES:
                tops.add(parts[0])
            elif len(parts) == 3 and parts[0] in ("src", "lib") and parts[1] not in NOT_PACKAGES:
                tops.add(parts[0] + "/" + parts[1])
        return sorted(tops) if len(tops) == 1 else []

    def attribute(self, blobs: dict, module: list[str], attr: str, anywhere: bool = False):
        """`pkg.attr`: in the module itself, or in a sibling module of that package."""
        tail = "/".join(module)
        files = [p for base in ("", "src/", "lib/") for p in (base + tail + ".py", base + tail + "/__init__.py")
                 if p in blobs]
        if not files and anywhere:
            files = depth_first(p for p in blobs if p.endswith(("/" + tail + ".py", "/" + tail + "/__init__.py"))
                                and not matches(p, CLOSURE_EXCLUDE))
        for path in files:
            if self.read(blobs, path, ("attr", attr)):
                return path, ("attr", attr)
            if path.endswith("/__init__.py"):
                folder = path[:-len("__init__.py")]
                for sibling in sorted(p for p in blobs if p.startswith(folder) and p.endswith(".py")
                                      and "/" not in p[len(folder):]):
                    if self.read(blobs, sibling, ("attr", attr)):
                        return sibling, ("attr", attr)
        return None


def tag_label(name: str) -> str:
    """The version a tag-derived build gives a tag: an optional `word-` prefix and a leading `v`
    are dropped, as setuptools_scm does."""
    m = re.match(r"^(?:[\w-]+-)?[vV]?(\d[^+]*)(?:\+.*)?$", name)
    return m.group(1) if m else name


def publication_points(repo: str, at: str, limit: int, tag_globs: list[str] | None):
    """→ ([(commit, date, name)] oldest first, how many there were before the cut, tags that do
    not point at a commit, tags left out by --tags). This is the design decision of all of v2."""
    if at == "commits":
        total = int(git(["rev-list", "--count", "HEAD"], repo).strip() or 0)
        log = git(["log", f"-{limit}", "--format=%H\t%ad\t%s", "--date=short"], repo)
        return [tuple(l.split("\t", 2)) for l in log.splitlines() if l.count("\t") >= 2][::-1], total, 0, 0
    out = git(["for-each-ref", "--sort=creatordate",
               "--format=%(objectname)\t%(creatordate:short)\t%(refname)", "refs/tags"], repo)
    pts, not_commits, filtered = [], 0, 0
    for l in out.splitlines():
        if l.count("\t") < 2:
            continue
        sha, date, name = l.split("\t", 2)
        # the full ref name: `refname:short` becomes `tags/v1` when a branch `v1` exists
        name = name[len("refs/tags/"):] if name.startswith("refs/tags/") else name
        if tag_globs and not any(fnmatch.fnmatchcase(name, g) for g in tag_globs):
            filtered += 1
            continue
        # resolve annotated tags; a tag that points at a blob or a tree is counted, not scanned
        c = git(["rev-parse", "--verify", "--quiet", sha + "^{commit}"], repo, may_fail=True).strip()
        if not c:
            not_commits += 1
            continue
        pts.append((c, date, name))
    return pts[-limit:], len(pts), not_commits, filtered


def declared_version(objects: Objects, entries, path: str, pattern: str, seen: dict) -> str | None:
    for p, kind, oid in entries:
        if p == path and kind == "blob":
            if (oid, pattern) not in seen:
                seen[(oid, pattern)] = bounded_search(pattern, objects.text(oid))
            return seen[(oid, pattern)]
    return None


class Labels:
    """The label at a publication point, and where it was read from."""

    def __init__(self, objects: Objects, fixed: tuple[str, str] | None):
        self.objects, self.fixed = objects, fixed
        self.sources, self.seen = Sources(objects), {}
        self.counts: dict[str, int] = {}
        self.previous, self.conflicts = None, 0

    def source(self, entries):
        if self.fixed:
            return self.fixed
        return self.sources.find({path: oid for path, kind, oid in entries if kind == "blob"})

    def at(self, entries, tag: str | None, count: bool = True) -> str | None:
        if self.fixed:
            src = self.fixed
            label = declared_version(self.objects, entries, src[0], src[1], self.seen)
            if label is None and src[1] == DEFAULT_VERSION_REGEX:      # a file that is just the version
                for path, kind, oid in entries:
                    if path == src[0] and kind == "blob" and len(self.objects.text(oid).split()) == 1 \
                            and plausible(self.objects.text(oid).strip()):
                        label = self.objects.text(oid).strip()
        else:
            blobs = {path: oid for path, kind, oid in entries if kind == "blob"}
            src = self.sources.find(blobs)
            if src is None:
                return None
            if src[0] == TAG_SOURCE:
                label = tag_label(tag) if tag else None
            else:
                label = self.sources.read(blobs, *src)
            # the source changed since the last point, and the earlier one still declares
            # something else here: two files disagree about the version of this commit
            if (count and label and self.previous and self.previous != src
                    and TAG_SOURCE not in (src[0], self.previous[0])):
                other = self.sources.read(blobs, *self.previous)
                if other and other != label:
                    self.conflicts += 1
            if count and label:
                self.previous = src
        if label and count:
            self.counts[src[0]] = self.counts.get(src[0], 0) + 1
        return label


CONFIG_KEYS = {"at": str, "version_file": str, "version_regex": str, "closure": list, "tags": list}


def read_config(repo: str) -> dict:
    """`.closure-drift.json`, checked. A broken file, a wrong type or an unknown key is a refusal."""
    cfg_path = Path(repo) / ".closure-drift.json"
    if not cfg_path.exists():
        return {}
    try:
        cfg = json.loads(cfg_path.read_bytes().decode("utf-8"))
    except (ValueError, OSError, RecursionError) as e:
        raise Refusal(f"broken {printable(cfg_path)}: {printable(e)}")
    if not isinstance(cfg, dict):
        raise Refusal(f"broken {printable(cfg_path)}: it must hold a JSON object, not {type(cfg).__name__}")
    for key, value in cfg.items():
        if key not in CONFIG_KEYS:
            raise Refusal(f"broken {printable(cfg_path)}: unknown key {printable(repr(key))}; "
                          f"known keys are {', '.join(sorted(CONFIG_KEYS))}")
        if not isinstance(value, CONFIG_KEYS[key]) or not value:
            raise Refusal(f"broken {printable(cfg_path)}: {key!r} must be a non-empty "
                          f"{'list of globs' if CONFIG_KEYS[key] is list else 'string'}")
        if isinstance(value, list) and any(not isinstance(g, str) or not g for g in value):
            raise Refusal(f"broken {printable(cfg_path)}: every entry of {key!r} must be a non-empty string")
    return cfg


def working_tree_state(repo: str) -> tuple[bool | None, str | None]:
    """(dirty, why it was not checked). `git status` would run a clean filter named in the
    repository's config; where one is defined the check is not made, and the report says so."""
    local = local_config(repo)
    if local is None:
        return None, "not checked: the local git config could not be read"
    for key, _value in local:
        if re.match(r"^filter\..*\.(clean|smudge|process)$", key) or key.startswith("include"):
            return None, f"not checked: the repository's own git config sets {printable(key)}"
    status = git_bytes(["status", "--porcelain"], repo, may_fail=True)
    if status is None:
        return None, "not checked: this repository has no working tree"
    return bool(status.strip()), None


def explain(objects: Objects, closure: Closure, states: dict) -> dict:
    """Which paths differ between the first closure a label named and each of the others.
    Printed only when asked for: the report otherwise lists no file of the closure."""
    fulls = list(states)
    first = {p: (k, o) for p, k, o in closure.members(objects.entries(states[fulls[0]]["commit"]))}
    out = {"first": {"closure": states[fulls[0]]["key"], "point": states[fulls[0]]["where"]}, "others": []}
    for full in fulls[1:]:
        other = {p: (k, o) for p, k, o in closure.members(objects.entries(states[full]["commit"]))}
        out["others"].append({
            "closure": states[full]["key"], "point": states[full]["where"],
            "changed": sorted(p for p in first if p in other and first[p] != other[p]),
            "only_in_first": sorted(p for p in first if p not in other),
            "only_in_other": sorted(p for p in other if p not in first),
        })
    return out


def badge(verdict: str, head: str) -> str:
    colour = {"clean": "brightgreen", "would_be_clean": "brightgreen",
              "drift": "red", "would_drift": "red"}.get(verdict, "lightgrey")
    message = f"{verdict} @ {head}"
    quoted = message.replace("-", "--").replace("_", "__").replace(" ", "_").replace("@", "%40")
    return (f"![version labels: {message}]"
            f"(https://img.shields.io/badge/version_labels-{quoted}-{colour})")


def run() -> int:
    ap = argparse.ArgumentParser(
        description="Does your version label name exactly one version of your code?")
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--at", choices=["tags", "commits"], default=None,
                    help="where artefacts are published (default: tags, or the repo's config file)")
    ap.add_argument("--would-tag", action="store_true",
                    help="before tagging: would HEAD reuse a label that already names other code?")
    ap.add_argument("--tags", action="append", metavar="GLOB",
                    help="only tags matching this glob are publication points (repeatable)")
    ap.add_argument("--closure", action="append", help="glob of files that determine your output")
    ap.add_argument("--strict", action="store_true",
                    help="clean only if every publication point scanned was compared")
    ap.add_argument("--explain", metavar="LABEL",
                    help="list the paths that differ under a label in drift")
    ap.add_argument("--version-file")
    ap.add_argument("--version-regex")
    ap.add_argument("--max-commits", type=int, default=400,
                    help="most recent publication points to scan (default 400)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--badge", action="store_true",
                    help="print one line of Markdown: a badge naming the verdict and the commit measured")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"),
                    help="compare two tags or commits: labels, closures, and the paths that differ")
    ap.add_argument("--diagnose", action="store_true",
                    help="add what a bug report needs: versions, options, what could not be read")
    ap.add_argument("--version", action="store_true", help="print the version and exit")
    a = ap.parse_args()

    if a.version:
        print(f"closure_drift {__version__}")
        return 0
    if a.diagnose and a.badge:
        raise Refusal("--diagnose and --badge are two outputs; pass one")
    if a.diagnose:
        diagnose_start(a)

    if a.max_commits < 1:
        raise Refusal(f"--max-commits must be 1 or more, got {a.max_commits}")
    if a.json and a.badge:
        raise Refusal("--json and --badge are two outputs; pass one")
    if git_bytes(["rev-parse", "--git-dir"], a.repo, may_fail=True) is None:
        raise Refusal(f"not a git repository: {printable(a.repo)}")
    head_sha = git(["rev-parse", "--verify", "--quiet", "HEAD^{commit}"], a.repo, may_fail=True).strip()
    if not head_sha:
        raise Refusal(f"this repository has no commits: {printable(a.repo)}")

    if a.diagnose:
        diagnose_repository(a)
    # A partial clone fetches what it lacks; on a git that cannot disable that, it is refused.
    partial = [k for k, _v in (local_config(a.repo) or [])
               if k == "extensions.partialclone" or re.match(r"^remote\..*\.(promisor|partialclonefilter)$", k)]
    if partial and git_version() < (2, 45):
        raise Refusal("this is a partial clone, and this git is older than 2.45: reading an object "
                      "that is not here would fetch it, running the remote's configured commands. "
                      "Use git 2.45 or newer, or a full clone.")
    # settings committed in the repository; command-line flags override them
    cfg = read_config(a.repo)

    at = a.at or cfg.get("at") or "tags"
    if at not in ("tags", "commits"):
        raise Refusal(f"invalid 'at' in .closure-drift.json: {printable(repr(at))}")
    if at == "commits" and a.would_tag:
        raise Refusal("--would-tag asks about a tag; it cannot be combined with --at commits")
    if at == "commits" and a.tags:
        raise Refusal("--tags selects tags; it cannot be combined with --at commits")
    if a.would_tag and (a.strict or a.explain):
        raise Refusal("--would-tag answers about one commit; --strict and --explain do not apply to it")
    if a.compare and (a.would_tag or a.explain or a.strict or a.tags or a.at == "commits"):
        raise Refusal("--compare looks at exactly two references; --would-tag, --explain, --strict, "
                      "--tags and --at commits do not apply to it")
    tag_globs = (a.tags or cfg.get("tags")) if at == "tags" else None
    check_globs(tag_globs or [], "--tags")
    check_globs(a.closure or cfg.get("closure") or [], "--closure")

    vfile = a.version_file or cfg.get("version_file")
    vregex = a.version_regex or cfg.get("version_regex")
    if vregex and not vfile:
        raise Refusal("--version-regex needs --version-file (or version_file in "
                      ".closure-drift.json): on its own it would be discarded, unchecked.")

    objects = Objects(a.repo)
    try:
        return measure(a, objects, head_sha, at, tag_globs, vfile, vregex, cfg)
    finally:
        objects.close()


def measure(a, objects: Objects, head_sha: str, at: str, tag_globs, vfile, vregex, cfg) -> int:
    head_entries = objects.entries(head_sha)
    labels = Labels(objects, (vfile, vregex or DEFAULT_VERSION_REGEX) if vfile else None)
    vsrc = labels.source(head_entries)
    vpath, vpat = (vsrc[0], vsrc[1] if vfile else None) if vsrc else (None, None)
    if vpath == TAG_SOURCE and at == "commits":
        raise Refusal("the version of this project is derived from the tag at build time, and "
                      "--at commits has no tag to read it from. Pass --version-file if a file declares it.")
    # a malformed pattern, or one without a capture group, is refused before anything is read
    try:
        _probe = re.compile(vpat or "()")
    except (re.error, RecursionError, OverflowError) as e:
        raise Refusal(f"invalid --version-regex {vpat!r}: {e}")
    if _probe.groups < 1:
        raise Refusal(f"--version-regex {vpat!r} has no capture group: "
                      "the pattern must capture the version label, e.g. 'version = \"([^\"]+)\"'.")
    include = a.closure or cfg.get("closure") or CLOSURE_DEFAULTS
    closure = Closure(include)

    if a.compare:
        return compare(a, objects, closure, labels, vpath, include, head_sha)

    # --would-tag looks at every tag: a collision with an old tag is a collision
    limit = a.max_commits if not a.would_tag else 10 ** 9
    pts, total, not_commits, filtered = publication_points(a.repo, at, limit, tag_globs)
    if not pts and (not a.would_tag or (tag_globs and filtered)):
        msg = ("no tags found — this repository publishes nothing addressable by tag. "
               "If it publishes continuously, rerun with --at commits.")
        if tag_globs and filtered:
            msg = (f"no tag matches --tags {printable(' '.join(tag_globs))}: "
                   f"{filtered} tag(s) were left out and none remain.")
        if a.json:
            emit({"report_format": REPORT_FORMAT, "verdict": "no_publication_points", "note": msg})
        else:
            print(msg, file=sys.stderr)
        return 2

    # label -> full closure id -> {key (the 16-hex id), where it was first seen, commit}
    by_label: dict[str, dict[str, dict]] = defaultdict(dict)
    churn, compared, no_label, empty = 0, 0, 0, 0
    empty_labelled: dict[str, list[str]] = defaultdict(list)   # label -> tags whose closure is empty
    prev = None
    for sha, date, name in pts:
        entries = objects.entries(sha)
        short, full, nfiles = closure.ids(entries)
        if nfiles == 0:
            empty += 1
            if a.would_tag:
                v = labels.at(entries, name if at == "tags" else None, count=False)
                if v:
                    empty_labelled[v].append(f"{name} ({date})")
            continue
        v = labels.at(entries, name if at == "tags" else None)
        if v:
            states = by_label[v]
            if full not in states:
                taken = sum(1 for s in states.values() if s["key"].split("~")[0] == short)
                states[full] = {"key": short if not taken else f"{short}~{taken + 1}",
                                "where": f"{name} ({date})", "commit": sha, "name": name}
            compared += 1
        else:
            no_label += 1
        if prev is not None and full != prev:
            churn += 1
        prev = full

    if not labels.counts and vsrc is None and not a.would_tag:
        raise Refusal("could not find a version label. Pass --version-file / --version-regex.\n"
                      "tried: pyproject.toml, setup.cfg, setup.py and the project's own package; "
                      "Cargo.toml, package.json, composer.json, build.gradle, VERSION, version.txt.")
    if not (a.json or a.badge):
        print(f"repository        {printable(a.repo)}")
        print(f"version from      {printable(vpath or '(nothing at HEAD)')}")
        print(f"closure           {printable(', '.join(include))}")
        print(f"publication point {at} ({len(pts)} scanned"
              + (f", the most recent of {total}" if total > len(pts) else "")
              + (f"; --tags {printable(' '.join(tag_globs))}" if tag_globs else "") + ")\n")

    drifting = {v: cs for v, cs in by_label.items() if len(cs) > 1}
    worst = max((len(cs) for cs in by_label.values()), default=0)
    truncated = total > len(pts)

    # tag families: colliding tags with different prefixes (`py-1.2.0`, `rs-1.2.0`) are pointed out
    families: dict[str, int] = {}
    if at == "tags":
        for cs in drifting.values():
            for s in cs.values():
                m = re.match(r"^(.*?)[vV]?\d", s["name"])
                prefix = m.group(1) if m else s["name"]
                families[prefix] = families.get(prefix, 0) + 1
    if len(families) < 2:
        families = {}

    dirty, dirty_note = working_tree_state(a.repo)
    # the report says which HEAD and which detector produced it
    stamp = {
        "measured_at_head": head_sha[:12],
        "working_tree_dirty": dirty,
        "detector_closure": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
    }
    if dirty_note:
        stamp["working_tree_dirty_note"] = dirty_note
    coverage = {
        "publication_points_scanned": len(pts),
        "publication_points_compared": compared,
        "points_without_label": no_label,
        "points_with_empty_closure": empty,
        "points_not_commits": not_commits,
        "range_truncated": truncated,
        "points_with_conflicting_sources": labels.conflicts,
    }
    if tag_globs:
        coverage["tag_globs"] = tag_globs
        coverage["tags_filtered_out"] = filtered

    if a.would_tag:
        return would_tag(a, closure, head_entries, labels, vpath, by_label,
                         drifting, stamp, coverage, at, include, dirty, dirty_note, empty_labelled)

    if drifting:
        verdict = "drift"
    elif empty == len(pts):
        verdict = "empty_closure"
    elif not by_label:
        verdict = "no_labels"
    elif len(by_label) == 1:
        verdict = "inconclusive"
    elif labels.conflicts or (a.strict and (no_label or empty or truncated)):
        verdict = "incomplete"
    else:
        verdict = "clean"
    # 0 is `clean` and nothing else: an absence of measurement is not a pass
    code = {"clean": 0, "drift": 1}.get(verdict, 2)

    explained = None
    if a.explain is not None:
        if a.explain not in drifting:
            raise Refusal(f"--explain {a.explain!r}: that label does not cover more than one closure "
                          "over the range scanned" + (f"; labels in drift: "
                          f"{printable(', '.join(sorted(drifting)[:10]))}" if drifting else "."))
        explained = explain(objects, closure, drifting[a.explain])
        explained["label"] = a.explain

    if a.badge:
        print(badge(verdict, stamp["measured_at_head"]))
        return code

    if a.json:
        report = {
            "report_format": REPORT_FORMAT,
            "stamp": stamp,
            "repo": a.repo, "version_file": vpath, "closure_globs": include,
            "published_at": at, "publication_points": compared + no_label, "labels": len(by_label),
            "labels_covering_multiple_closures": len(drifting),
            "max_closures_per_label": worst, "verdict": verdict,
            "drift": {v: {s["key"]: s["where"] for s in cs.values()} for v, cs in drifting.items()},
            "closure_ids": {s["key"]: full for cs in drifting.values() for full, s in cs.items()},
            "closure_changes_between_points": churn,
            "label_sources": dict(sorted(labels.counts.items())),
        }
        report.update(coverage)
        if families:
            report["tag_families"] = dict(sorted(families.items()))
        if explained:
            report["explain"] = explained
        emit(report)
        return code

    print(f"{'label':28s} {'closures':>9s}")
    print("-" * 44)
    for v, cs in sorted(by_label.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:25]:
        flag = "  <-- names more than one" if len(cs) > 1 else ""
        print(f"{printable(v)[:28]:28s} {len(cs):>9d}{flag}")
    if len(by_label) > 25:
        print(f"... and {len(by_label) - 25} more labels")

    if drifting:
        print("\nthe same label at two publications, with different code:")
        for v, cs in list(drifting.items())[:6]:
            print(f"  {printable(v)}")
            for s in cs.values():
                print(f"      closure {s['key']}  first at {printable(s['where'])}")

    if explained:
        print(f"\nwhat differs under {printable(a.explain)}, against {printable(explained['first']['point'])}:")
        for other in explained["others"]:
            print(f"  {printable(other['point'])}")
            for title, key in (("changed", "changed"), ("only in the first", "only_in_first"),
                               ("only here", "only_in_other")):
                for p in other[key][:40]:
                    print(f"      {title:18s} {printable(p)}")
                if len(other[key]) > 40:
                    print(f"      {title:18s} ... and {len(other[key]) - 40} more")

    print("\n" + "=" * 62)
    if verdict == "drift":
        print(f"DRIFT: {len(drifting)} of {len(by_label)} labels name more than one closure")
        print(f"at a publication point. The worst covers {worst}.")
        print("\nAn artefact addressed by (input, version) is ambiguous for those labels:")
        print("the same address denotes more than one possible output.")
        if not explained:
            print("Run again with --explain LABEL to list the paths that differ.")
        if families:
            names = sorted(f for f in families if f)
            print("\nThe tags in drift carry different prefixes: "
                  + ", ".join(shlex.quote(printable(f) + "*") if f else "(none)" for f in sorted(families)) + ".")
            print("If each prefix releases a different artefact from one version file, measure one")
            print("family at a time" + (f": --tags {shlex.quote(printable(names[0]) + '*')}" if names else "") + ".")
    elif verdict == "empty_closure":
        print("EMPTY CLOSURE: the closure globs match no file at any publication point scanned.")
        print("Nothing was compared. Pass --closure with the files that determine your output.")
    elif verdict == "no_labels":
        print("NO LABELS: no publication point declared a version. Nothing to compare.")
    elif verdict == "inconclusive":
        print("INCONCLUSIVE: only one distinct label across the range scanned.")
    elif verdict == "incomplete":
        print("INCOMPLETE: no label names more than one closure, but not every publication point")
        print("scanned could be compared with confidence. See the counts below.")
    else:
        print(f"CLEAN: each of the {len(by_label)} labels names exactly one closure at publication.")
        print(f"Your version label identifies your code, over the {compared} points compared.")

    print_coverage(coverage, a.max_commits, total)
    print_sources(labels)
    print(f"\nBetween publication points the closure changed {churn} time(s). That is development,")
    print("not drift, and is reported only so the two are never confused.")
    print_method(stamp, dirty, dirty_note)
    return code


def would_tag(a, closure, head_entries, labels, vpath, by_label, drifting,
              stamp, coverage, at, include, dirty, dirty_note, empty_labelled) -> int:
    """Before tagging: the label and closure of HEAD against the tags that exist. The answer is
    about the tag you are about to create; drift already in the history is counted, not judged."""
    short, full, nfiles = closure.ids(head_entries)
    label = labels.at(head_entries, None, count=False) if nfiles else None
    collides = []
    if nfiles == 0:
        verdict = "empty_closure_at_head"
    elif not label:
        verdict = "no_label_at_head"
    else:
        collides = [s["where"] for f, s in by_label.get(label, {}).items() if f != full]
        collides += empty_labelled.get(label, [])        # same label, and no code where HEAD has some
        verdict = "would_drift" if collides else "would_be_clean"
    code = {"would_be_clean": 0, "would_drift": 1}.get(verdict, 2)

    if a.badge:
        print(badge(verdict, stamp["measured_at_head"]))
        return code
    if a.json:
        report = {
            "report_format": REPORT_FORMAT, "stamp": stamp, "mode": "would_tag",
            "repo": a.repo, "version_file": vpath, "closure_globs": include, "published_at": at,
            "verdict": verdict, "label_at_head": label, "label_source": vpath,
            "closure_at_head": short if nfiles else None, "closure_id_at_head": full if nfiles else None,
            "collides_with": collides, "existing_drift_labels": len(drifting),
        }
        report.update(coverage)
        emit(report)
        return code

    print(f"commit            {stamp['measured_at_head']}"
          + ("   (the commit is measured, not the modified working tree)" if dirty else ""))
    print(f"label at HEAD     {printable(label) if label else '(none declared)'}")
    print(f"closure at HEAD   {short if nfiles else '(no file matches the closure globs)'}")
    print("\n" + "=" * 62)
    if verdict == "would_drift":
        print(f"WOULD DRIFT: the label {printable(label)} already names different code at:")
        for where in collides[:10]:
            print(f"      {printable(where)}")
        print("\nTagging this commit would make one label name more than one closure.")
        print("Change the version before you tag. To see what differs:")
        print(f"      --compare {shlex.quote(printable(collides[0].rsplit(' (', 1)[0]))} HEAD")
    elif verdict == "would_be_clean":
        print(f"WOULD BE CLEAN: no existing tag declares {printable(label)} with different code.")
    elif verdict == "no_label_at_head" and vpath == TAG_SOURCE:
        print("NO LABEL AT HEAD: this project derives its version from the tag, so the label will be")
        print("the tag you create. There is no version file to check before tagging.")
    elif verdict == "no_label_at_head":
        print(f"NO LABEL AT HEAD: {printable(vpath)} declares no version at this commit.")
    else:
        print("EMPTY CLOSURE AT HEAD: the closure globs match no file at this commit.")
    if drifting:
        print(f"\n{len(drifting)} label(s) already in drift in the existing tags. That is history,")
        print("and is not what this answer is about; run without --would-tag to see it.")
    print_coverage(coverage, a.max_commits, None)
    print_method(stamp, dirty, dirty_note)
    return code


def compare(a, objects, closure, labels, vpath, include, head_sha) -> int:
    """Two references, side by side: the label and closure of each, and the paths of the closure
    that differ. It looks at exactly these two commits; publication points play no part."""
    sides = []
    for ref in a.compare:
        # a name that is a tag is read as that tag, for the commit and for the label alike
        tag = git(["rev-parse", "--verify", "--quiet", "--end-of-options", "refs/tags/" + ref + "^{commit}"],
                  a.repo, may_fail=True).strip()
        sha = tag or git(["rev-parse", "--verify", "--quiet", "--end-of-options", ref + "^{commit}"],
                         a.repo, may_fail=True).strip()
        if not sha:
            raise Refusal(f"--compare: {printable(repr(ref))} does not name a commit in this repository")
        entries = objects.entries(sha)
        short, full, n = closure.ids(entries)
        src = labels.source(entries)
        sides.append({"ref": ref, "commit": sha[:12],
                      "label": labels.at(entries, ref if tag else None, count=False),
                      "label_source": src[0] if src else None,
                      "closure": short if n else None, "closure_id": full if n else None,
                      "files": n,
                      "members": {p: (k, o) for p, k, o in closure.members(entries)}})
    one, two = sides
    ma, mb = one.pop("members"), two.pop("members")
    changed = sorted(p for p in ma if p in mb and ma[p] != mb[p])
    only_a = sorted(p for p in ma if p not in mb)
    only_b = sorted(p for p in mb if p not in ma)
    if one["files"] and two["files"] and one["closure_id"] == two["closure_id"]:
        verdict = "identical"
    elif not (one["files"] and two["files"] and one["label"] and two["label"]):
        verdict = "not_comparable"
    elif one["label"] == two["label"]:
        verdict = "differs_under_one_label"
    else:
        verdict = "differs_under_two_labels"
    code = {"identical": 0, "differs_under_two_labels": 0, "differs_under_one_label": 1}.get(verdict, 2)

    dirty, dirty_note = working_tree_state(a.repo)
    stamp = {"measured_at_head": head_sha[:12], "working_tree_dirty": dirty,
             "detector_closure": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]}
    if dirty_note:
        stamp["working_tree_dirty_note"] = dirty_note
    if a.badge:
        print(badge(verdict, stamp["measured_at_head"]))
        return code
    if a.json:
        emit({"report_format": REPORT_FORMAT, "stamp": stamp, "mode": "compare", "repo": a.repo,
              "version_file": vpath, "closure_globs": include, "verdict": verdict,
              "a": one, "b": two, "changed": changed, "only_in_a": only_a, "only_in_b": only_b})
        return code

    for side, tag in ((one, "A"), (two, "B")):
        print(f"{tag}  {printable(side['ref'])}  (commit {side['commit']})")
        print(f"   label    {printable(side['label']) if side['label'] else '(none declared)'}")
        print(f"   closure  {side['closure'] or '(no file matches the closure globs)'}"
              + (f"   {side['files']} file(s)" if side["files"] else ""))
    for title, paths in (("changed", changed), ("only in A", only_a), ("only in B", only_b)):
        for p in paths[:60]:
            print(f"   {title:10s} {printable(p)}")
        if len(paths) > 60:
            print(f"   {title:10s} ... and {len(paths) - 60} more")
    print("\n" + "=" * 62)
    if verdict == "identical":
        print("IDENTICAL: the two references hold the same closure.")
    elif verdict == "differs_under_one_label":
        print(f"DIFFERS UNDER ONE LABEL: both declare {printable(one['label'])}, and the code differs")
        print(f"in {len(changed) + len(only_a) + len(only_b)} path(s). If both were published, that label names two things.")
    elif verdict == "differs_under_two_labels":
        print(f"DIFFERS UNDER TWO LABELS: {printable(one['label'])} and {printable(two['label'])}. "
              "The code differs and so does the label.")
    else:
        print("NOT COMPARABLE: a label or a closure is missing on one side (see above).")
    print_method(stamp, dirty, dirty_note)
    return code


def diagnose_start(a) -> None:
    """What a bug report needs and a user cannot be asked to look up: the versions involved and
    the options in effect. No version label, no path of the repository, no path inside a closure."""
    try:
        r = subprocess.run([*GIT, "--version"], capture_output=True, env=git_env())
        git_version = r.stdout.decode("utf-8", "replace").strip() or "unknown"
    except OSError:
        git_version = "git could not be run"
    DIAGNOSTICS.update({
        "detector_version": __version__,
        "detector_closure": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "git": git_version,
        "options": {"at": a.at, "would_tag": a.would_tag, "strict": a.strict, "json": a.json,
                    "max_commits": a.max_commits, "tags_globs_given": len(a.tags or []),
                    "closure_globs_given": len(a.closure or []),
                    "version_file_given": bool(a.version_file), "version_regex_given": bool(a.version_regex),
                    "explain_given": a.explain is not None, "compare_given": bool(a.compare)},
        "repository": None,
    })
    if not a.json:
        d = DIAGNOSTICS
        print(f"diagnostics       closure_drift {d['detector_version']} ({d['detector_closure']}), "
              f"Python {d['python']} on {d['platform']}, {printable(d['git'])}")
        print("  options         " + printable(", ".join(f"{k}={v}" for k, v in d["options"].items()
                                                         if v not in (None, False, 0))) or "(defaults)")


def diagnose_repository(a) -> None:
    def ask(*args):
        out = git(list(args), a.repo, may_fail=True).strip()
        return out or None
    tags = git(["for-each-ref", "--format=x", "refs/tags"], a.repo, may_fail=True)
    DIAGNOSTICS["repository"] = {
        "bare": ask("rev-parse", "--is-bare-repository"),
        "shallow": ask("rev-parse", "--is-shallow-repository"),
        "object_format": ask("rev-parse", "--show-object-format"),
        "tags": len(tags.splitlines()),
        "commits_reachable_from_head": ask("rev-list", "--count", "HEAD"),
        "config_file_present": (Path(a.repo) / ".closure-drift.json").exists(),
    }
    if not a.json:
        print("  repository      " + ", ".join(f"{k}={v}" for k, v in DIAGNOSTICS["repository"].items()) + "\n")


def print_sources(labels) -> None:
    if len(labels.counts) > 1:
        print("  labels were read from: " + ", ".join(
            f"{printable(k)} ({n})" for k, n in sorted(labels.counts.items())) + ".")
    if labels.conflicts:
        print(f"  at {labels.conflicts} point(s) the source changed and the earlier file still declares")
        print("  a different version there: two files disagree, and that is never reported as clean.")
        print("  Pass --version-file to say which one declares the version.")


def print_coverage(c: dict, max_commits: int, total) -> None:
    # what was not compared, said every time
    print(f"\nPublication points: {c['publication_points_scanned']} scanned, "
          f"{c['publication_points_compared']} compared.")
    if c["points_without_label"]:
        print(f"  {c['points_without_label']} declared no version label there and were not compared.")
    if c["points_with_empty_closure"]:
        print(f"  {c['points_with_empty_closure']} had no file matching the closure globs and were not compared.")
    if c["points_not_commits"]:
        print(f"  {c['points_not_commits']} tag(s) do not point at a commit and were not scanned.")
    if c.get("tags_filtered_out"):
        print(f"  {c['tags_filtered_out']} tag(s) do not match --tags and were not scanned.")
    if c["range_truncated"]:
        print(f"  older points are outside --max-commits {max_commits} and were not scanned"
              + (f" ({total - c['publication_points_scanned']} of them)." if total else "."))


def print_method(stamp: dict, dirty, dirty_note) -> None:
    print("\nMethod: closure = SHA-256 over (path, git object id) for files matching the closure")
    print("globs, evaluated at each publication point. Adjust --closure / --at if these do not")
    print("describe how your output is produced and published.")
    print(f"\nMeasured at HEAD {stamp['measured_at_head']}"
          + (" (working tree DIRTY)" if dirty else "")
          + (f" (working tree {dirty_note})" if dirty_note else "")
          + f", detector closure {stamp['detector_closure']}.")
    print("This report is itself addressed by those two values. A finding without them is a")
    print("finding you cannot return to — which is the defect this tool reports.")


def main() -> int:
    """The closed set of exit codes is enforced here: nothing leaves this function as a traceback,
    and nothing that is not a measured drift leaves it as 1."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    try:
        if sys.argv[1:] == ["--match-on-stdin"]:
            return match_on_stdin()
        return run()
    except Refusal as e:
        print(str(e), file=sys.stderr)
        return 2
    except BrokenPipeError:
        # The reader went away (`| head -1`). Nothing was determined for it; say so by the code.
        try:
            sys.stdout = open(os.devnull, "w")
        except OSError:
            pass
        return 2
    except Exception as e:  # noqa: BLE001 — the guard is the point
        print(f"internal error ({type(e).__name__}): no measurement was produced. "
              "This is a defect in closure_drift; please report it.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
