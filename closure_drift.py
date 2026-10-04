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
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

__version__ = "0.9.0"
REPORT_FORMAT = 2

# (file, regex with one capture group) — first match in the repo wins
VERSION_SOURCES = [
    ("package.json",   r'"version"\s*:\s*"([^"]+)"'),
    ("pyproject.toml", r'^\s*version\s*=\s*["\']([^"\']+)["\']'),
    ("Cargo.toml",     r'^\s*version\s*=\s*["\']([^"\']+)["\']'),
    ("setup.py",       r'(?<![\w.])version\s*=\s*["\']([^"\']+)["\']'),
    ("setup.py",       r'^(?:VERSION|version|__version__)\s*=\s*["\']([^"\']+)["\']'),
    ("composer.json",  r'"version"\s*:\s*"([^"]+)"'),
    ("build.gradle",   r'^\s*version\s*=?\s*["\']([^"\']+)["\']'),
    ("VERSION",        r'^\s*(\S+)\s*$'),
    ("version.txt",    r'^\s*(\S+)\s*$'),
]

# A version kept in a module rather than in the build file.
VERSION_ATTR = r'^\s*(?:__version__|VERSION|version)\s*(?::[^=\n]*)?=\s*["\']([^"\']+)["\']'
DUNDER_ATTR = r'^\s*__version__\s*(?::[^=\n]*)?=\s*["\']([^"\']+)["\']'
ONE_TOKEN = r'^\s*(\S+)\s*$'
VERSION_MODULES = ("__version__.py", "_version.py", "version.py", "__about__.py", "__init__.py")
BUILD_FILES = ("pyproject.toml", "setup.cfg", "setup.py")
TAG_SOURCE = "(the tag)"      # the label is the tag name: the version is derived from it at build time
DEFAULT_VERSION_REGEX = r'"?version"?\s*[:=]\s*["\']([^"\']+)["\']'
BUILT_IN_PATTERNS = ({p for _, p in VERSION_SOURCES}
                     | {DEFAULT_VERSION_REGEX, VERSION_ATTR, DUNDER_ATTR, ONE_TOKEN})

# Build tools that take the version from the tag itself.
TAG_DERIVED = ("setuptools_scm", "setuptools-scm", "hatch-vcs", "hatch_vcs", "versioneer",
               "poetry-dynamic-versioning", "dunamai", "versioningit", "pbr")

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


def attr_pattern(name: str) -> str:
    """The pattern for `<name> = "..."`. Built from an escaped name, so it is safe to match in-process."""
    pattern = r'^\s*' + re.escape(name) + r'\s*(?::[^=\n]*)?=\s*["\']([^"\']+)["\']'
    BUILT_IN_PATTERNS.add(pattern)
    return pattern


def uncommented(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def module_files(dotted: list[str], blobs: dict) -> list[str]:
    """Where a dotted module name can live: at the root, under src/ or lib/, as a file or a package."""
    tail = "/".join(dotted)
    return [p for base in ("", "src/", "lib/") for p in (base + tail + ".py", base + tail + "/__init__.py")
            if p in blobs]


def depth_first(paths) -> list[str]:
    return sorted(paths, key=lambda p: (p.count("/"), p))


class Sources:
    """Where the version label is, at one commit. Resolved at every publication point: a project
    moves its version from setup.py to a module to pyproject.toml over the years, and a source
    chosen once at HEAD reads nothing at the older tags.

    In order: a pointer the build files declare; a version written in a known file; a tool that
    derives the version from the tag (then the label IS the tag); a module named in setup.py; the
    shallowest version module in the tree."""

    def __init__(self, objects: Objects):
        self.objects = objects
        self.cache: dict = {}

    def find(self, entries) -> tuple[str, str] | None:
        blobs = {path: oid for path, kind, oid in entries if kind == "blob"}
        key = tuple(blobs.get(n) for n in BUILD_FILES + tuple(f for f, _ in VERSION_SOURCES))
        hit = self.cache.get(key)
        if hit is not None and (hit[0] == TAG_SOURCE or self.reads(blobs, *hit)):
            return hit
        found, cacheable = self.resolve(blobs)
        if found is not None and cacheable:
            self.cache[key] = found
        return found

    def reads(self, blobs: dict, path: str, pattern: str) -> bool:
        return path in blobs and re.search(pattern, self.objects.text(blobs[path]), re.MULTILINE) is not None

    def resolve(self, blobs: dict):
        text = {n: uncommented(self.objects.text(blobs[n])) if n in blobs else "" for n in BUILD_FILES}
        pp, cfg, setup = text["pyproject.toml"], text["setup.cfg"], text["setup.py"]

        # 1. a pointer the build files declare
        m = re.search(r'^\[tool\.hatch\.version\][^\[]*?^\s*path\s*=\s*["\']([^"\']+)["\']', pp, re.M | re.S)
        if m and self.reads(blobs, m.group(1), VERSION_ATTR):
            return (m.group(1), VERSION_ATTR), True
        m = (re.search(r'^\s*version\s*=\s*\{\s*file\s*=\s*\[?\s*["\']([^"\']+)["\']', pp, re.M)
             or re.search(r'^\s*version\s*=\s*file:\s*(\S+)', cfg, re.M))
        if m and self.reads(blobs, m.group(1), ONE_TOKEN):
            return (m.group(1), ONE_TOKEN), True
        m = (re.search(r'^\s*version\s*=\s*\{\s*attr\s*=\s*["\']([\w.]+)["\']', pp, re.M)
             or re.search(r'^\s*version\s*=\s*attr:\s*([\w.]+)', cfg, re.M))
        if m and "." in m.group(1):
            got = self.attribute(blobs, m.group(1).split(".")[:-1], m.group(1).split(".")[-1])
            if got:
                return got, True
        if "flit_core" in pp or "flit.buildapi" in pp:
            m = re.search(r'^\s*name\s*=\s*["\']([^"\']+)["\']', pp, re.M)
            if m:
                got = self.attribute(blobs, [m.group(1).replace("-", "_")], "__version__")
                if got:
                    return got, True

        # 2. a version written in a known file
        for path, pattern in VERSION_SOURCES:
            if self.reads(blobs, path, pattern):
                return (path, pattern), True

        # 3. the version is derived from the tag at build time: the label is the tag
        if any(tool in body for body in text.values() for tool in TAG_DERIVED):
            return (TAG_SOURCE, ""), True

        # 4. setup.py names a module: version=pkg.__version__
        m = re.search(r'(?<![\w.])version\s*=\s*([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*[,)\n]', setup)
        if m:
            name, attr = m.group(1), m.group(2)
            anywhere = depth_first(p for p in blobs if p in (name + ".py", name + "/__init__.py")
                                   or p.endswith(("/" + name + ".py", "/" + name + "/__init__.py")))
            for path in anywhere:
                if self.reads(blobs, path, attr_pattern(attr)):
                    return (path, attr_pattern(attr)), True

        # 5. the shallowest version module, when this is a Python project at all
        if any(n in blobs for n in BUILD_FILES):
            for path in depth_first(p for p in blobs if p.count("/") <= 2
                                    and p.rsplit("/", 1)[-1] in VERSION_MODULES
                                    and not matches(p, CLOSURE_EXCLUDE)):
                pattern = DUNDER_ATTR if path.endswith("__init__.py") else VERSION_ATTR
                if self.reads(blobs, path, pattern):
                    return (path, pattern), False
        return None, False

    def attribute(self, blobs: dict, module: list[str], attr: str) -> tuple[str, str] | None:
        """`pkg.__version__`: in the module itself, or in a version module of that package."""
        for path in module_files(module, blobs):
            if self.reads(blobs, path, attr_pattern(attr)):
                return path, attr_pattern(attr)
            folder = path.rsplit("/", 1)[0] + "/" if path.endswith("__init__.py") else None
            for name in VERSION_MODULES[:-1]:
                if folder and self.reads(blobs, folder + name, VERSION_ATTR):
                    return folder + name, VERSION_ATTR
        return None


def tag_label(name: str) -> str:
    """The version a tag-derived build gives a tag: the name, without a leading `v`."""
    return name[1:] if re.match(r"^[vV]\d", name) else name


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

    def source(self, entries) -> tuple[str, str] | None:
        return self.fixed or self.sources.find(entries)

    def at(self, entries, tag: str | None, count: bool = True) -> str | None:
        src = self.source(entries)
        if src is None:
            return None
        if src[0] == TAG_SOURCE:
            label = tag_label(tag) if tag else None
        else:
            label = declared_version(self.objects, entries, src[0], src[1], self.seen)
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
    if vfile:
        vsrc = labels.fixed
    else:
        vsrc = labels.source(head_entries)
        if not vsrc:
            raise Refusal("could not find a version label. Pass --version-file / --version-regex.\n"
                          f"tried: {', '.join(p for p, _ in VERSION_SOURCES)}, "
                          "and dynamic-version fallbacks.")
    vpath, vpat = vsrc
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

    plain = not (a.json or a.badge)
    if plain:
        print(f"repository        {printable(a.repo)}")
        print(f"version from      {printable(vpath)}")
        print(f"closure           {printable(', '.join(include))}")
        print(f"publication point {at} ({len(pts)} scanned"
              + (f", the most recent of {total}" if total > len(pts) else "")
              + (f"; --tags {printable(' '.join(tag_globs))}" if tag_globs else "") + ")\n")

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
    elif a.strict and (no_label or empty or truncated):
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
        print("scanned could be compared, and --strict was asked for. See the counts below.")
    else:
        print(f"CLEAN: each of the {len(by_label)} labels names exactly one closure at publication.")
        print(f"Your version label identifies your code, over the {compared} points compared.")

    print_coverage(coverage, a.max_commits, total)
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
            "verdict": verdict, "label_at_head": label,
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
        sha = git(["rev-parse", "--verify", "--quiet", "--end-of-options", ref + "^{commit}"],
                  a.repo, may_fail=True).strip()
        if not sha:
            raise Refusal(f"--compare: {printable(repr(ref))} does not name a commit in this repository")
        entries = objects.entries(sha)
        short, full, n = closure.ids(entries)
        sides.append({"ref": ref, "commit": sha[:12],
                      "label": labels.at(entries, ref if git_bytes(
                          ["rev-parse", "--verify", "--quiet", "--end-of-options", "refs/tags/" + ref],
                          a.repo, may_fail=True) else None, count=False),
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
