#!/usr/bin/env python3
"""closure_drift — does your version label name exactly one version of your code?

When you publish an artefact and address it by (input, version), that address is sound only if the
version identifies exactly one state of the producing code. Nothing enforces it: the label is a
string a human edits. When two code states share a label, one address denotes two outputs, and the
system cannot notice — the label is the only thing it recorded.

This tool measures that on any git repository, read-only, with no dependencies.

WHERE THIS TOOL CHANGED ITS MIND (v2, and it matters)

v1 compared the label against the closure at EVERY COMMIT, and reported drift whenever a commit
changed the closure without changing the label. Run against four widely used public repositories,
it reported drift on all of them — because between two releases the version label does not move
while the code does. That is not drift. That is how releases work. A detector that fires on every
repository in the world is worth exactly what a test that never fails is worth, which is the very
failure this tool exists to expose.

The phenomenon is real only where an ARTEFACT WAS PUBLISHED under the label. So v2 asks where your
publication points are:

  --at tags      (default) each tag is a publication. Drift = two publications, same label,
                 different closure. This is the case for libraries, packages, most software.
  --at commits   every commit publishes (continuous publication: a site, a feed, a daily edition).
                 Then every commit is a publication point and v1's question was the right one.

Between publication points the closure moves freely and that is reported as development churn —
counted, never alarmed.

Usage
  closure_drift.py                              # auto-detect, drift at tags
  closure_drift.py --would-tag                  # before you tag: would this commit reuse a label?
  closure_drift.py --tags 'v*'                  # only these tags are publication points
  closure_drift.py --at commits                 # continuously published output
  closure_drift.py --closure 'src/**/*.py'      # say what determines your output
  closure_drift.py --strict                     # clean only if every point scanned was compared
  closure_drift.py --explain 1.4.2              # which paths differ under a label in drift
  closure_drift.py --version-file pyproject.toml --version-regex '...'
  closure_drift.py --json | --badge

Exit codes, closed set
  0   clean (or, with --would-tag, would_be_clean). Nothing else ends at 0.
  1   drift (or would_drift) — a label covers more than one closure AT A PUBLICATION POINT.
  2   no determination, cause named: a refusal on stderr, or a report whose verdict is
      inconclusive, incomplete, no_labels, empty_closure, no_publication_points,
      no_label_at_head or empty_closure_at_head.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPORT_FORMAT = 2

# (file, regex with one capture group) — first match in the repo wins
VERSION_SOURCES = [
    ("package.json",   r'"version"\s*:\s*"([^"]+)"'),
    ("pyproject.toml", r'^\s*version\s*=\s*["\']([^"\']+)["\']'),
    ("Cargo.toml",     r'^\s*version\s*=\s*["\']([^"\']+)["\']'),
    ("setup.py",       r'version\s*=\s*["\']([^"\']+)["\']'),
    ("composer.json",  r'"version"\s*:\s*"([^"]+)"'),
    ("build.gradle",   r'^\s*version\s*=?\s*["\']([^"\']+)["\']'),
    ("VERSION",        r'^\s*(\S+)\s*$'),
    ("version.txt",    r'^\s*(\S+)\s*$'),
]

# Where the version hides when pyproject.toml declares `dynamic = ["version"]` — which today is the
# NORM in Python, not the exception. v1 answered "inconclusive" on those repositories, that is: it
# failed on the majority case and called its own failure a result.
DYNAMIC_HINTS = [
    (r'^\s*__version__\s*=\s*["\']([^"\']+)["\']', ["src/*/__version__.py", "*/__version__.py",
                                                    "src/*/_version.py", "*/_version.py",
                                                    "src/*/version.py", "*/version.py",
                                                    "src/*/__init__.py", "*/__init__.py"]),
]
DEFAULT_VERSION_REGEX = r'"?version"?\s*[:=]\s*["\']([^"\']+)["\']'
BUILT_IN_PATTERNS = ({p for _, p in VERSION_SOURCES} | {p for p, _ in DYNAMIC_HINTS}
                     | {DEFAULT_VERSION_REGEX})

CLOSURE_DEFAULTS = ["src/**", "lib/**", "app/**", "*.py", "*.js", "*.ts", "*.rs", "*.go", "*.java"]

# never part of a closure: churn that cannot change behaviour
CLOSURE_EXCLUDE = ["**/test/**", "**/tests/**", "**/*_test.*", "**/*.test.*", "**/spec/**",
                   "**/docs/**", "**/*.md", "**/node_modules/**", "**/vendor/**", "**/.git/**"]

# Seconds one version pattern may spend on one version file. A pattern can come from the measured
# repository's own `.closure-drift.json`, and a pattern can be written to never finish.
REGEX_BUDGET = 5


class Refusal(Exception):
    """A named reason why no measurement was produced. Always exit 2, never a traceback."""


# Every git call goes through GIT and git_env(). Fixed for all of them:
#   - `core.fsmonitor=false`: a repository's own config can name a command there, and `git status`
#     runs it. Measuring a repository must not execute what that repository says to execute.
#   - `--no-optional-locks`: `git status` otherwise refreshes the index, which is a write to the
#     repository this tool promises never to write to.
#   - `--no-replace-objects`: a ref under refs/replace/ makes git hand back a different object than
#     the one named. Measured: one replace ref turned a real `drift` into `inconclusive`.
GIT = ["git", "--no-optional-locks", "--no-replace-objects", "-c", "core.fsmonitor=false"]

# Variables that make git read a repository other than the one named on the command line. With
# GIT_DIR set in the caller's shell, `git -C <path>` measures GIT_DIR and the report still prints
# <path>: a `clean` about the wrong repository. They are removed, not obeyed.
REDIRECTING = ("GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
               "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_NAMESPACE", "GIT_GRAFT_FILE",
               "GIT_SHALLOW_FILE", "GIT_REPLACE_REF_BASE", "GIT_CONFIG")


def git_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in REDIRECTING}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", GIT_NO_REPLACE_OBJECTS="1", LC_ALL="C")
    return env


def git_bytes(args: list[str], repo: str, may_fail: bool = False) -> bytes | None:
    """Output of a git command. A failure is a Refusal naming the command — unless the caller
    says failure is an answer (may_fail), in which case it is None. It is never empty output:
    0.7.1 read a failed call as "nothing there", and a tag git could not read became a tag that
    was quietly not compared."""
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


def printable(text) -> str:
    """Text safe to print: control characters, bidirectional overrides and undecodable bytes are
    written as escapes. A version label is a string someone else chose; printed raw, a label
    holding a line break can draw a second verdict line under the real one."""
    out = []
    for ch in str(text):
        o = ord(ch)
        if (o < 32 or 127 <= o < 160 or 0xD800 <= o <= 0xDFFF or o in (0x2028, 0x2029)
                or 0x202A <= o <= 0x202E or 0x2066 <= o <= 0x2069):
            out.append("\\x%02x" % o if o < 256 else "\\u%04x" % o)
        else:
            out.append(ch)
    return "".join(out)


def matches(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path, g.replace("**/", "*/"))
               or (g.endswith("/**") and path.startswith(g[:-3] + "/")) for g in globs)


class Objects:
    """One `git cat-file --batch` for the whole run, and a memory of every tree already read.

    Up to 0.7.1 each publication point cost one `ls-tree -r` and one `show`: two processes per
    tag, and every path of every tag matched against every glob again. Between two tags most
    folders do not change, and git already says so — an unchanged folder is the same tree object.
    Each tree object is read once; so is each version file.

    Reading the objects directly also means no path is ever quoted: `ls-tree` without `-z` quotes
    and octal-escapes any path that is not plain ASCII, the quoted form matches no glob, and the
    file silently leaves the closure. Measured on 0.7.1: two tags under one label differing only
    in `src/ação.py` came back `inconclusive`.
    """

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
        while i < len(raw):
            space = raw.index(b" ", i)
            nul = raw.index(b"\0", space)
            mode, name = raw[i:space], raw[space + 1:nul]
            oid = raw[nul + 1:nul + 1 + width].hex()
            i = nul + 1 + width
            kind = "tree" if mode in (b"40000", b"040000") else "commit" if mode == b"160000" else "blob"
            out.append((name, kind, oid))
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
        """(short id, full id, number of files).

        The short id is SHA-256 over path + object id, first 16 hex: the value every version since
        0.3.0 has printed, kept so that published closures stay comparable. It joins path and
        object id with nothing between them, so two different lists of files can hash the same
        bytes — `src/a` (blob X) + `src/b` (blob Y) and the single file `src/a<X>src/b` (blob Y).
        Identity is therefore decided by the full id: all 64 hex over `path NUL type SP id LF`.

        A submodule pointer (type `commit`) is part of the closure when its path matches: the
        commit it names decides what code is there. Up to 0.7.1 it was skipped.
        """
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
    """The label a pattern captures in a text, or None — within REGEX_BUDGET seconds.

    A built-in pattern is matched here. Any other pattern is matched in a child process of this
    same file, because a pattern can be written so that matching never ends, and Python offers no
    way to interrupt a match from inside the process. The child receives the pattern and the text
    on standard input and nothing else."""
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


def detect_version_source(objects: Objects, head: list[tuple[str, str, str]]) -> tuple[str, str] | None:
    blobs = {path: oid for path, kind, oid in head if kind == "blob"}
    for path, pattern in VERSION_SOURCES:
        if path not in blobs:
            continue
        txt = objects.text(blobs[path])
        if re.search(pattern, txt, re.MULTILINE):
            return path, pattern
        # the file declares a dynamic version: the label exists, it is just not here
        if "dynamic" in txt and "version" in txt:
            for pat, globs in DYNAMIC_HINTS:
                for cand in sorted(f for f in blobs if matches(f, globs)):
                    if re.search(pat, objects.text(blobs[cand]), re.MULTILINE):
                        return cand, pat
    return None


def publication_points(repo: str, at: str, limit: int, tag_globs: list[str] | None):
    """→ ([(commit, date, name)] oldest first, how many there were before the cut, tags that do
    not point at a commit, tags left out by --tags). This is the design decision of all of v2."""
    if at == "commits":
        total = int(git(["rev-list", "--count", "HEAD"], repo).strip() or 0)
        log = git(["log", f"-{limit}", "--format=%H\t%ad\t%s", "--date=short"], repo)
        return [tuple(l.split("\t", 2)) for l in log.splitlines() if l.count("\t") >= 2][::-1], total, 0, 0
    out = git(["for-each-ref", "--sort=creatordate",
               "--format=%(objectname)\t%(creatordate:short)\t%(refname:short)", "refs/tags"], repo)
    pts, not_commits, filtered = [], 0, 0
    for l in out.splitlines():
        if l.count("\t") < 2:
            continue
        sha, date, name = l.split("\t", 2)
        if tag_globs and not any(fnmatch.fnmatchcase(name, g) for g in tag_globs):
            filtered += 1
            continue
        # An annotated tag points at a tag object; resolve it to the commit. A tag may also point
        # at a blob or a tree (a public key, for instance): that is not a publication of code, and
        # it is counted instead of bringing the measurement down.
        c = git(["rev-parse", "--verify", "--quiet", sha + "^{commit}"], repo, may_fail=True).strip()
        if not c:
            not_commits += 1
            continue
        pts.append((c, date, name))
    return pts[-limit:], len(pts), not_commits, filtered


def declared_version(objects: Objects, entries, path: str, pattern: str, seen: dict) -> str | None:
    for p, kind, oid in entries:
        if p == path and kind == "blob":
            if oid not in seen:
                seen[oid] = bounded_search(pattern, objects.text(oid))
            return seen[oid]
    return None


CONFIG_KEYS = {"at": str, "version_file": str, "version_regex": str, "closure": list, "tags": list}


def read_config(repo: str) -> dict:
    """`.closure-drift.json`, checked. A broken file is a refusal, never silently ignored — and
    "broken" includes a file that parses and is not what it should be: a key this tool does not
    know is more likely a misspelt key than a comment, and ignoring it measures something other
    than what the repository declared."""
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
    """(dirty, why it was not checked). `git status` runs the clean filter of any modified file
    that `.gitattributes` routes through one, and a filter is a command named in the repository's
    own config. Where the local config defines one, the check is not made and the report says so:
    an unknown is honest, running someone else's command to find out is not."""
    local = git_bytes(["config", "--local", "--list", "-z"], repo, may_fail=True)
    if local is None:
        return None, "not checked: the local git config could not be read"
    for item in local.decode("utf-8", "replace").split("\0"):
        key = item.split("\n", 1)[0].lower()
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
    a = ap.parse_args()

    if a.max_commits < 1:
        raise Refusal(f"--max-commits must be 1 or more, got {a.max_commits}")
    if a.json and a.badge:
        raise Refusal("--json and --badge are two outputs; pass one")
    if git_bytes(["rev-parse", "--git-dir"], a.repo, may_fail=True) is None:
        raise Refusal(f"not a git repository: {printable(a.repo)}")
    head_sha = git(["rev-parse", "--verify", "--quiet", "HEAD^{commit}"], a.repo, may_fail=True).strip()
    if not head_sha:
        raise Refusal(f"this repository has no commits: {printable(a.repo)}")

    # A repository may carry its own measurement settings in `.closure-drift.json` at the root:
    #   {"at": "commits", "version_file": "...", "version_regex": "...", "closure": ["glob", ...],
    #    "tags": ["glob", ...]}
    # This exists because the honest configuration for a continuously-publishing system is four
    # long flags, and a measurement that takes four flags does not get run — not in CI, and not
    # when someone says "show me" with thirty seconds and no notes. Committing the configuration
    # next to the code also makes the measurement itself reviewable: the flags become part of the
    # repository's history instead of part of someone's shell history.
    # CLI flags override the file. A broken file is an error, never silently ignored — a tool that
    # measures claims cannot guess what you meant.
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
    tag_globs = (a.tags or cfg.get("tags")) if at == "tags" else None

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
    if vfile:
        vsrc = (vfile, vregex or DEFAULT_VERSION_REGEX)
    else:
        vsrc = detect_version_source(objects, head_entries)
        if not vsrc:
            raise Refusal("could not find a version label. Pass --version-file / --version-regex.\n"
                          f"tried: {', '.join(p for p, _ in VERSION_SOURCES)}, "
                          "and dynamic-version fallbacks.")
    vpath, vpat = vsrc
    # 2026-09-15 — a malformed pattern, or one without a capture group, used to raise:
    # `re.error` / `IndexError` left the instrument with exit 1, which is the code for
    # `drift`. An error that cannot be told apart from a finding is worse than no finding.
    # Both are now refusals with the refusal code, named, before any repository is read.
    try:
        _probe = re.compile(vpat)
    except (re.error, RecursionError, OverflowError) as e:
        raise Refusal(f"invalid --version-regex {vpat!r}: {e}")
    if _probe.groups < 1:
        raise Refusal(f"--version-regex {vpat!r} has no capture group: "
                      "the pattern must capture the version label, e.g. 'version = \"([^\"]+)\"'.")
    include = a.closure or cfg.get("closure") or CLOSURE_DEFAULTS
    closure = Closure(include)

    pts, total, not_commits, filtered = publication_points(a.repo, at, a.max_commits, tag_globs)
    if not pts and not a.would_tag:
        msg = ("no tags found — this repository publishes nothing addressable by tag. "
               "If it publishes continuously, rerun with --at commits.")
        if tag_globs and filtered:
            msg = (f"no tag matches --tags {printable(' '.join(tag_globs))}: "
                   f"{filtered} tag(s) were left out and none remain.")
        print(json.dumps({"report_format": REPORT_FORMAT, "verdict": "no_publication_points",
                          "note": msg}, indent=1) if a.json else msg,
              file=sys.stderr if not a.json else sys.stdout)
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
    seen_labels: dict = {}
    churn, compared, no_label, empty = 0, 0, 0, 0
    prev = None
    for sha, date, name in pts:
        entries = objects.entries(sha)
        short, full, nfiles = closure.ids(entries)
        if nfiles == 0:
            empty += 1
            continue
        v = declared_version(objects, entries, vpath, vpat, seen_labels)
        if v:
            states = by_label[v]
            if full not in states:
                taken = sum(1 for s in states.values() if s["key"].split("~")[0] == short)
                states[full] = {"key": short if not taken else f"{short}~{taken + 1}",
                                "where": f"{name} ({date})", "commit": sha}
            compared += 1
        else:
            no_label += 1
        if prev is not None and full != prev:
            churn += 1
        prev = full

    drifting = {v: cs for v, cs in by_label.items() if len(cs) > 1}
    worst = max((len(cs) for cs in by_label.values()), default=0)
    truncated = total > len(pts)

    dirty, dirty_note = working_tree_state(a.repo)
    # The stamp of the report itself. A report that says "your label covers N states of your code"
    # and does not say under which HEAD, nor with which version of the detector, it was measured
    # is itself an ambiguously addressed artefact — the defect this program exists to find. It goes
    # in the JSON because the JSON is what becomes the record.
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
        return would_tag(a, objects, closure, head_entries, vpath, vpat, seen_labels, by_label,
                         drifting, stamp, coverage, at, include, dirty)

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
    # 0 is `clean` and nothing else. Up to 0.7.1 `inconclusive` and `no_labels` also ended at 0,
    # so `closure_drift.py && release` went ahead on a repository about which nothing had been
    # established. An absence of measurement is not a pass.
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
        }
        report.update(coverage)
        if explained:
            report["explain"] = explained
        print(json.dumps(report, indent=1))
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


def would_tag(a, objects, closure, head_entries, vpath, vpat, seen_labels, by_label, drifting,
              stamp, coverage, at, include, dirty) -> int:
    """Before tagging: the label and closure of HEAD against the tags that exist. The answer is
    about the tag you are about to create; drift already in the history is counted, not judged."""
    short, full, nfiles = closure.ids(head_entries)
    label = declared_version(objects, head_entries, vpath, vpat, seen_labels) if nfiles else None
    collides = []
    if nfiles == 0:
        verdict = "empty_closure_at_head"
    elif not label:
        verdict = "no_label_at_head"
    else:
        collides = [s["where"] for f, s in by_label.get(label, {}).items() if f != full]
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
        print(json.dumps(report, indent=1))
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
        print("Change the version before you tag.")
    elif verdict == "would_be_clean":
        print(f"WOULD BE CLEAN: no existing tag declares {printable(label)} with different code.")
    elif verdict == "no_label_at_head":
        print(f"NO LABEL AT HEAD: {printable(vpath)} declares no version at this commit.")
    else:
        print("EMPTY CLOSURE AT HEAD: the closure globs match no file at this commit.")
    if drifting:
        print(f"\n{len(drifting)} label(s) already in drift in the existing tags. That is history,")
        print("and is not what this answer is about; run without --would-tag to see it.")
    print_coverage(coverage, a.max_commits, None)
    print_method(stamp, dirty, None)
    return code


def print_coverage(c: dict, max_commits: int, total) -> None:
    # What was NOT compared, said every time. A `clean` over half the tags is a different claim
    # from a `clean` over all of them, and 0.7.1 printed the same line for both.
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
