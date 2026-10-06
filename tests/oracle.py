#!/usr/bin/env python3
"""Independent oracle for closure_drift, written from tests/ORACLE_SPEC.md alone.

Usage:
  oracle.py REPO --version-file F --version-regex R [--closure G]... [--tags G]... [--strict]
  oracle.py REPO --compare A B [--closure G]...
  oracle.py --self-test

Prints one JSON object on stdout and exits 0 when it produced an answer (the detector's
would-be exit code is in the "exit" field). On a git failure: reason on stderr, exit 3.
Python 3.9+, standard library only.
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
import tempfile

# ---------------------------------------------------------------------------
# Defaults (section 3)

DEFAULT_INCLUDE = ["src/**", "lib/**", "app/**", "*.py", "*.js", "*.ts", "*.rs", "*.go", "*.java"]
EXCLUDE = ["**/test/**", "**/tests/**", "**/*_test.*", "**/*.test.*", "**/spec/**", "**/docs/**",
           "**/*.md", "**/node_modules/**", "**/vendor/**", "**/.git/**"]

_STRIPPED_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                 "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_NAMESPACE")


class GitError(Exception):
    pass


# ---------------------------------------------------------------------------
# Git access

def _git_env():
    env = dict(os.environ)
    for k in _STRIPPED_ENV:
        env.pop(k, None)
    return env


def _git(repo, args, check=True, stdin=None):
    cmd = ["git", "--no-replace-objects", "-C", repo] + list(args)
    try:
        p = subprocess.run(cmd, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env=_git_env())
    except OSError as e:
        raise GitError("cannot run git: %s" % e)
    if check and p.returncode != 0:
        raise GitError("git %s failed (%d): %s" % (
            " ".join(str(a) for a in args[:3]), p.returncode,
            p.stderr.decode("utf-8", "replace").strip()))
    return p


def _dec(b):
    return b.decode("utf-8", "surrogateescape")


def _rev_commit(repo, rev):
    """Return the commit id rev^{commit} resolves to, or None."""
    p = _git(repo, ["rev-parse", "--verify", "-q", rev + "^{commit}"], check=False)
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    return out.decode("ascii") if out else None


def ls_tree_entries(repo, commit):
    """Section 1: list of (mode, type, oid, path_bytes) in git's order; blob and commit kept."""
    p = _git(repo, ["ls-tree", "-r", "-z", "--full-tree", commit])
    out = []
    for rec in p.stdout.split(b"\0"):
        if not rec:
            continue
        tab = rec.index(b"\t")
        head, path = rec[:tab], rec[tab + 1:]
        mode, typ, oid = head.split(b" ")
        typ = typ.decode("ascii")
        if typ not in ("blob", "commit"):
            continue
        out.append((mode.decode("ascii"), typ, oid.decode("ascii"), path))
    return out


# ---------------------------------------------------------------------------
# Glob language (section 2), own translation to a regular expression

def _lit(ch):
    cp = ord(ch)
    return "\\U%08x" % cp


def _translate(glob):
    """Translate one glob to a regex string matched with fullmatch (DOTALL not needed: no '.')."""
    i, n = 0, len(glob)
    parts = []
    ANY = "[\\s\\S]"
    while i < n:
        c = glob[i]
        if c == "*":
            while i < n and glob[i] == "*":
                i += 1
            parts.append(ANY + "*")
            continue
        if c == "?":
            parts.append(ANY)
            i += 1
            continue
        if c == "[":
            j = i + 1
            neg = False
            if j < n and glob[j] == "!":
                neg = True
                j += 1
            start = j
            if j < n and glob[j] == "]":
                j += 1  # ']' first in the set is literal
            close = glob.find("]", j)
            if close < 0:
                parts.append(_lit("["))  # '[' with no closing ']' is literal
                i += 1
                continue
            body = glob[start:close]
            items = []
            k = 0
            while k < len(body):
                if k + 2 < len(body) and body[k + 1] == "-":
                    lo, hi = body[k], body[k + 2]
                    if ord(lo) <= ord(hi):
                        items.append(_lit(lo) + "-" + _lit(hi))
                    # reversed range: contributes nothing
                    k += 3
                else:
                    items.append(_lit(body[k]))
                    k += 1
            if not items:
                parts.append(ANY if neg else "(?!)")
            else:
                parts.append("[" + ("^" if neg else "") + "".join(items) + "]")
            i = close + 1
            continue
        parts.append(_lit(c))
        i += 1
    return "".join(parts)


_glob_cache = {}


class _Glob(object):
    __slots__ = ("rx", "rx2", "prefix")

    def __init__(self, g):
        self.rx = re.compile(_translate(g))
        self.rx2 = re.compile(_translate(g[3:])) if g.startswith("**/") else None
        self.prefix = (g[:-3] + "/") if g.endswith("/**") else None

    def match(self, path):
        if self.rx.fullmatch(path):
            return True
        if self.rx2 is not None and self.rx2.fullmatch(path):
            return True
        if self.prefix is not None and path.startswith(self.prefix):
            return True
        return False


def _compiled(g):
    c = _glob_cache.get(g)
    if c is None:
        c = _Glob(g)
        _glob_cache[g] = c
    return c


def matches(path, glob):
    """Section 2: does `path` (str) match `glob` under the three rules."""
    return _compiled(glob).match(path)


# ---------------------------------------------------------------------------
# Closure (section 3)

def _is_name_glob(g):
    """Amendment 3: '**/' followed by text with no '/' is matched against the file name."""
    return g.startswith("**/") and "/" not in g[3:]


_EXC_PATH = [g for g in EXCLUDE if not _is_name_glob(g)]
_EXC_NAME = [g for g in EXCLUDE if _is_name_glob(g)]


def excluded(path):
    """Section 3 + Amendment 3: is `path` (str) excluded by some exclude glob."""
    name = path.rsplit("/", 1)[-1]
    return (any(_compiled(g).match(path) for g in _EXC_PATH)
            or any(_compiled(g).match(name) for g in _EXC_NAME))


def _members(entries, include):
    inc = [_compiled(g) for g in include]
    out = []
    for e in entries:
        p = _dec(e[3])
        if any(g.match(p) for g in inc) and not excluded(p):
            out.append(e)
    return out


def _ids(members):
    full = hashlib.sha256()
    short = hashlib.sha256()
    for (_mode, typ, oid, path) in members:
        full.update(path + b"\0" + typ.encode("ascii") + b" " + oid.encode("ascii") + b"\n")
        short.update(path + oid.encode("ascii"))
    return short.hexdigest()[:16], full.hexdigest()


class _Repo(object):
    def __init__(self, repo, closure):
        self.repo = repo
        self.include = list(closure) if closure else list(DEFAULT_INCLUDE)
        self._entries = {}
        self._blobs = {}

    def entries(self, commit):
        e = self._entries.get(commit)
        if e is None:
            e = ls_tree_entries(self.repo, commit)
            self._entries[commit] = e
        return e

    def members(self, commit):
        return _members(self.entries(commit), self.include)

    def blob(self, oid):
        b = self._blobs.get(oid)
        if b is None:
            b = _git(self.repo, ["cat-file", "blob", oid]).stdout
            self._blobs[oid] = b
        return b


def closure_of(repo, commit, closure=None):
    """Closure of a commit (any revision peeling to a commit)."""
    oid = _rev_commit(repo, commit)
    if oid is None:
        raise GitError("cannot resolve %r to a commit" % commit)
    r = _Repo(repo, closure)
    m = r.members(oid)
    short, full = _ids(m)
    return {"closure_id": full, "closure": short, "files": len(m)}


# ---------------------------------------------------------------------------
# Publication points (section 4)

def _publication_points(repo, tags):
    fmt = "%(refname)%00%(objectname)%00%(objecttype)%00%(*objectname)%00%(*objecttype)"
    p = _git(repo, ["for-each-ref", "--format=" + fmt, "refs/tags/"])
    points = []  # (name, commit)
    not_commits = 0
    filtered = 0
    for line in p.stdout.split(b"\n"):
        if not line:
            continue
        refname, obj, otype, pobj, ptype = line.split(b"\0")
        refname_s = _dec(refname)
        if otype == b"commit":
            commit = obj.decode("ascii")
        elif otype == b"tag" and ptype == b"commit":
            commit = pobj.decode("ascii")
        elif otype == b"tag":
            # peeled type not a commit as reported, or nested tags: ask rev-parse
            commit = _rev_commit(repo, refname_s)
        else:
            commit = None
        if commit is None:
            not_commits += 1
            continue
        name = refname_s[len("refs/tags/"):]
        if tags and not any(fnmatch.fnmatchcase(name, g) for g in tags):
            filtered += 1
            continue
        points.append((name, commit))
    return points, not_commits, filtered


# ---------------------------------------------------------------------------
# Label (section 5)

def _label(r, commit, version_file, rx):
    for (_mode, typ, oid, path) in r.entries(commit):
        if typ == "blob" and _dec(path) == version_file:
            text = r.blob(oid).decode("utf-8", "replace")
            m = rx.search(text)
            if not m:
                return None
            return label_from_match(m)
    return None


def label_from_match(m):
    """Section 5 + Amendment 2: named groups (by group number) joined, else group 1."""
    gi = m.re.groupindex
    if gi:
        out = ""
        for _name, num in sorted(gi.items(), key=lambda kv: kv[1]):
            v = m.group(num)
            if v is None or v == "":
                continue
            if out == "" or v[0] in "-+":
                out += v
            else:
                out += "." + v
        return out if out else None
    g = m.group(1)
    return g if g else None


# ---------------------------------------------------------------------------
# Full run (section 6)

def full_run(repo, version_file, version_regex, closure=None, tags=None, strict=False):
    rx = re.compile(version_regex, re.MULTILINE)
    r = _Repo(repo, closure)
    points, not_commits, filtered = _publication_points(repo, tags)
    out_points = {}
    label_ids = {}  # label -> set of full ids
    n_empty = 0
    n_nolabel = 0
    n_compared = 0
    for name, commit in points:
        m = r.members(commit)
        if not m:
            n_empty += 1
            out_points[name] = {"commit": commit, "label": None, "closure_id": None,
                                "closure": None, "files": 0}
            continue
        short, full = _ids(m)
        lab = _label(r, commit, version_file, rx)
        if lab is None:
            n_nolabel += 1
        else:
            n_compared += 1
            label_ids.setdefault(lab, set()).add(full)
        out_points[name] = {"commit": commit, "label": lab, "closure_id": full,
                            "closure": short, "files": len(m)}

    drifting = dict((lab, sorted(ids)) for lab, ids in sorted(label_ids.items()) if len(ids) >= 2)
    if not points:
        verdict, code = "no_publication_points", 2
    elif drifting:
        verdict, code = "drift", 1
    elif n_empty == len(points):
        verdict, code = "empty_closure", 2
    elif not label_ids:
        verdict, code = "no_labels", 2
    elif len(label_ids) == 1:
        verdict, code = "inconclusive", 2
    elif strict and (n_empty or n_nolabel):
        verdict, code = "incomplete", 2
    elif n_compared < n_empty + n_nolabel:
        verdict, code = "incomplete", 2
    else:
        verdict, code = "clean", 0

    return {
        "verdict": verdict,
        "exit": code,
        "labels": sorted(label_ids),
        "labels_covering_multiple_closures": len(drifting),
        "max_closures_per_label": max([len(v) for v in label_ids.values()] or [0]),
        "publication_points_scanned": len(points),
        "publication_points_compared": n_compared,
        "points_without_label": n_nolabel,
        "points_with_empty_closure": n_empty,
        "points_not_commits": not_commits,
        "tags_filtered_out": filtered,
        "drifting": drifting,
        "points": out_points,
    }


# ---------------------------------------------------------------------------
# Compare (section 7)

def _resolve_ref(repo, name):
    c = _rev_commit(repo, "refs/tags/" + name)
    if c is None:
        c = _rev_commit(repo, name)
    if c is None:
        raise GitError("cannot resolve %r to a commit" % name)
    return c


def compare(repo, a, b, closure=None):
    r = _Repo(repo, closure)
    res = {}
    maps = []
    for key, ref in (("a", a), ("b", b)):
        commit = _resolve_ref(repo, ref)
        m = r.members(commit)
        short, full = _ids(m)
        res[key] = {"commit": commit, "closure_id": full, "closure": short, "files": len(m)}
        d = {}
        for (_mode, typ, oid, path) in m:
            d.setdefault(path, (typ, oid))
        maps.append(d)
    ma, mb = maps
    res["changed"] = sorted(_dec(p) for p in ma if p in mb and ma[p] != mb[p])
    res["only_in_a"] = sorted(_dec(p) for p in ma if p not in mb)
    res["only_in_b"] = sorted(_dec(p) for p in mb if p not in ma)
    return res


# ---------------------------------------------------------------------------
# Self-test (section 8)

def _blob_oid(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _sh(args, cwd=None, stdin=None):
    p = subprocess.run(["git"] + args, cwd=cwd, input=stdin, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, env=_git_env())
    if p.returncode != 0:
        raise RuntimeError("self-test setup: git %s: %s" % (args, p.stderr.decode("utf-8", "replace")))
    return p.stdout


def _build_repo(path, files_by_commit, extra_tags=True):
    """files_by_commit: list of (commit_name, {path_bytes: (mode, data_or_gitlink_oid)})."""
    _sh(["init", "-q", "--bare", "-b", "main", path])
    stream = []
    mark = 0
    commit_marks = {}
    t = 1700000000
    for idx, (cname, files) in enumerate(files_by_commit):
        blob_marks = {}
        for p, (mode, data) in files.items():
            if mode == "160000":
                continue
            mark += 1
            blob_marks[p] = mark
            stream.append(b"blob\nmark :%d\ndata %d\n" % (mark, len(data)) + data + b"\n")
        mark += 1
        commit_marks[cname] = mark
        msg = cname.encode("ascii")
        stream.append(b"commit refs/heads/%s\nmark :%d\ncommitter T <t@example.com> %d +0000\n"
                      b"data %d\n%s\n" % (cname.encode("ascii"), mark, t + idx, len(msg), msg))
        stream.append(b"deleteall\n")
        for p, (mode, data) in files.items():
            if mode == "160000":
                stream.append(b"M 160000 " + data + b" " + p + b"\n")
            else:
                stream.append(b"M " + mode.encode("ascii") + b" :%d " % blob_marks[p] + p + b"\n")
        stream.append(b"\n")
    marks_file = os.path.join(os.path.dirname(path), os.path.basename(path) + ".marks")
    _sh(["-C", path, "fast-import", "--quiet", "--export-marks=" + marks_file],
        stdin=b"".join(stream))
    with open(marks_file, "rb") as f:
        marks = dict((int(l.split()[0][1:]), l.split()[1].decode("ascii"))
                     for l in f.read().splitlines() if l)
    return dict((c, marks[m]) for c, m in commit_marks.items())


def self_test():
    results = []

    def check(name, got, exp):
        ok = got == exp
        results.append((name, ok))
        if not ok:
            print("FAIL %s\n  got: %r\n  exp: %r" % (name, got, exp))

    # --- glob language: every bullet of section 2 and the three rules
    G = [
        # '*' any run, empty included, '/' included
        ("*", "", True), ("*", "a/b/c", True), ("a*b", "ab", True), ("a*b", "a/x/y/b", True),
        ("a*b", "a/x/y/bc", False),
        # '**' same as '*'
        ("a**b", "a/x/b", True), ("**", "x/y", True), ("a***", "a/b", True),
        # '?' exactly one char, '/' included
        ("a?b", "a/b", True), ("a?b", "axb", True), ("a?b", "ab", False), ("a?b", "a//b", False),
        # [seq], [!seq], ranges, ']' first literal, unclosed '[' literal
        ("[abc]", "b", True), ("[abc]", "d", False), ("[abc]", "", False),
        ("[!abc]", "d", True), ("[!abc]", "/", True), ("[!abc]", "a", False),
        ("[a-c]x", "bx", True), ("[a-c]x", "dx", False), ("[a-]", "-", True),
        ("[]a]", "]", True), ("[]a]", "a", True), ("[]a]", "b", False),
        ("[!]a]", "b", True), ("[!]a]", "]", False),
        ("[ab", "[ab", True), ("[ab", "a", False), ("a[", "a[", True),
        ("[/]", "/", True), ("x[!/]y", "x/y", False),
        # anything else is itself
        ("a.b", "a.b", True), ("a.b", "axb", False), ("a+(b)$^", "a+(b)$^", True),
        ("a\\*", "a\\xyz", True), ("a\\*", "a*", False), ("a{b,c}", "ab", False),
        # case-sensitive everywhere
        ("*.PY", "a.py", False), ("*.py", "a.PY", False), ("*.py", "a.py", True),
        # rule 2
        ("**/x.py", "x.py", True), ("**/x.py", "a/b/x.py", True), ("**/x.py", "ax.py", False),
        ("**/test/**", "test/a", True), ("**/test/**", "a/test/b", True),
        ("**/test/**", "test", False), ("**/test/**", "atest/b", False),
        ("**/test/**", "a/test", False),
        # rule 3 (plain-text prefix)
        ("src/**", "src/a", True), ("src/**", "src", False), ("src/**", "srcx/a", False),
        ("s[r]c/**", "s[r]c/x", True), ("s[r]c/**", "src/x", True), ("s?c/**", "s?c/", True),
        ("s?c/**", "sxc/", True), ("[ab]/**", "c/x", False),
        # non-UTF-8 byte (surrogate-escaped) is one character
        ("src/?.py", b"src/\xff.py".decode("utf-8", "surrogateescape"), True),
        ("src/[!a].py", b"src/\xff.py".decode("utf-8", "surrogateescape"), True),
        # newline is a character like any other
        ("a*b", "a\nb", True), ("a?b", "a\nb", True),
    ]
    for g, p, exp in G:
        check("glob %r ~ %r" % (g, p), matches(p, g), exp)

    tmp = tempfile.mkdtemp(prefix="oracle-selftest-")
    try:
        gitlink = b"1234567890abcdef1234567890abcdef12345678"
        base = {
            b"src/a.py": ("100644", b"a1\n"),
            b"src/tests/t.py": ("100644", b"t1\n"),
            b"lib/x_test.go": ("100644", b"x\n"),
            b"x_test.py": ("100644", b"x\n"),
            b"README.md": ("100644", b"r\n"),
            b"docs/a.py": ("100644", b"d\n"),
            b"main.go": ("100755", b"package main\n"),
            b"link.py": ("120000", b"src/a.py"),
            b"lib/sub": ("160000", gitlink),
            b"src/\xff.py": ("100644", b"ff\n"),
            b"notes.txt": ("100644", b"n1\n"),
            b"VERSION": ("100644", b"version = 1.0\n"),
        }

        c1 = base
        c2 = dict(base); c2[b"src/a.py"] = ("100644", b"a2\n")
        c3 = dict(base); c3[b"VERSION"] = ("100644", b"version = 2.0\n"); c3[b"notes.txt"] = ("100644", b"n3\n")
        c4 = {b"notes.txt": ("100644", b"n4\n"), b"VERSION": ("100644", b"version = 3.0\n"),
              b"src/tests/t.py": ("100644", b"t\n")}
        c5 = dict(base); c5[b"VERSION"] = ("100644", b"nothing here\n")
        c6 = dict(base); c6[b"VERSION"] = ("100644", b"version = \n")
        c7 = dict(base); c7[b"src/tests/t.py"] = ("100644", b"t7\n")
        c8 = dict(base); del c8[b"VERSION"]  # no version file at all
        repo = os.path.join(tmp, "r.git")
        cm = _build_repo(repo, [("c1", c1), ("c2", c2), ("c3", c3), ("c4", c4), ("c5", c5),
                                ("c6", c6), ("c7", c7), ("c8", c8)])

        # hand-computed members of c1, in git order (byte order of full paths)
        exp_members = [
            (b"lib/sub", "commit", gitlink.decode("ascii")),
            (b"link.py", "blob", _blob_oid(b"src/a.py")),
            (b"main.go", "blob", _blob_oid(b"package main\n")),
            (b"src/a.py", "blob", _blob_oid(b"a1\n")),
            (b"src/\xff.py", "blob", _blob_oid(b"ff\n")),
        ]

        def hand_ids(members):
            fh = hashlib.sha256(b"".join(p + b"\0" + t.encode() + b" " + o.encode() + b"\n"
                                         for p, t, o in members)).hexdigest()
            sh = hashlib.sha256(b"".join(p + o.encode() for p, t, o in members)).hexdigest()[:16]
            return sh, fh

        s1, f1 = hand_ids(exp_members)
        exp_members2 = list(exp_members)
        exp_members2[3] = (b"src/a.py", "blob", _blob_oid(b"a2\n"))
        s2, f2 = hand_ids(exp_members2)

        co = closure_of(repo, cm["c1"])
        check("closure_of c1", co, {"closure_id": f1, "closure": s1, "files": 5})
        check("closure_of c3 == c1", closure_of(repo, cm["c3"])["closure_id"], f1)
        check("closure_of c7 == c1 (test-only change)", closure_of(repo, cm["c7"])["closure_id"], f1)
        check("closure_of c2", closure_of(repo, "c2"), {"closure_id": f2, "closure": s2, "files": 5})
        check("closure_of c4 files", closure_of(repo, "c4")["files"], 0)
        # explicit closure: only *.txt
        check("closure_of --closure *.txt", closure_of(repo, "c1", ["*.txt"]),
              dict(zip(("closure", "closure_id"),
                       hand_ids([(b"notes.txt", "blob", _blob_oid(b"n1\n"))])), files=1))

        # tags
        _sh(["-C", repo, "update-ref", "refs/tags/v1.0", cm["c1"]])
        tagobj = _sh(["-C", repo, "mktag"], stdin=(
            "object %s\ntype commit\ntag v1.0-again\ntagger T <t@example.com> 1700000000 +0000\n\nm\n"
            % cm["c2"]).encode()).strip().decode()
        _sh(["-C", repo, "update-ref", "refs/tags/v1.0-again", tagobj])
        nested = _sh(["-C", repo, "mktag"], stdin=(
            "object %s\ntype tag\ntag nested\ntagger T <t@example.com> 1700000000 +0000\n\nm\n"
            % tagobj).encode()).strip().decode()
        _sh(["-C", repo, "update-ref", "refs/tags/nested", nested])
        for name, c in (("r2", "c3"), ("e3", "c4"), ("n5", "c5"), ("m6", "c6"), ("s7", "c7"),
                        ("x8", "c8")):
            _sh(["-C", repo, "update-ref", "refs/tags/" + name, cm[c]])
        blob = _sh(["-C", repo, "hash-object", "-w", "--stdin"], stdin=b"just a blob\n").strip().decode()
        _sh(["-C", repo, "update-ref", "refs/tags/blobtag", blob])
        tree = _sh(["-C", repo, "rev-parse", cm["c1"] + "^{tree}"]).strip().decode()
        _sh(["-C", repo, "update-ref", "refs/tags/treetag", tree])
        tagtree = _sh(["-C", repo, "mktag"], stdin=(
            "object %s\ntype tree\ntag tagtree\ntagger T <t@example.com> 1700000000 +0000\n\nm\n"
            % tree).encode()).strip().decode()
        _sh(["-C", repo, "update-ref", "refs/tags/tagtree", tagtree])

        RX = r"^version = (.*)$"
        run = lambda **kw: full_run(repo, "VERSION", RX, **kw)

        # A: everything -> drift (label 1.0 with c1 and c2 closures)
        a = run()
        check("A verdict", (a["verdict"], a["exit"]), ("drift", 1))
        check("A labels", a["labels"], ["1.0", "2.0"])
        check("A drifting", a["drifting"], {"1.0": sorted([f1, f2])})
        check("A counts", (a["publication_points_scanned"], a["publication_points_compared"],
                           a["points_without_label"], a["points_with_empty_closure"],
                           a["points_not_commits"], a["tags_filtered_out"],
                           a["labels_covering_multiple_closures"], a["max_closures_per_label"]),
              (9, 5, 3, 1, 3, 0, 1, 2))
        check("A point v1.0", a["points"]["v1.0"],
              {"commit": cm["c1"], "label": "1.0", "closure_id": f1, "closure": s1, "files": 5})
        check("A point v1.0-again (annotated)", a["points"]["v1.0-again"],
              {"commit": cm["c2"], "label": "1.0", "closure_id": f2, "closure": s2, "files": 5})
        check("A point nested (tag of tag)", a["points"]["nested"]["commit"], cm["c2"])
        check("A point e3 (empty)", a["points"]["e3"],
              {"commit": cm["c4"], "label": None, "closure_id": None, "closure": None, "files": 0})
        check("A point n5 (no match)", a["points"]["n5"]["label"], None)
        check("A point m6 (empty capture)", (a["points"]["m6"]["label"], a["points"]["m6"]["closure_id"]),
              (None, f1))
        check("A point x8 (no version file)", a["points"]["x8"]["label"], None)
        check("A non-commit tags absent", sorted(k for k in ("blobtag", "treetag", "tagtree")
                                                 if k in a["points"]), [])
        check("A JSON serialisable", isinstance(json.dumps(a), str), True)

        # drift beats empty
        d = run(tags=["v1.0*", "e3"])
        check("drift over empty", (d["verdict"], d["exit"], d["tags_filtered_out"]), ("drift", 1, 6))
        # every point empty
        e = run(tags=["e3"])
        check("empty_closure", (e["verdict"], e["exit"], e["labels"]), ("empty_closure", 2, []))
        # no label
        n = run(tags=["e3", "n5", "m6"])
        check("no_labels", (n["verdict"], n["exit"]), ("no_labels", 2))
        # exactly one distinct label
        i = run(tags=["v1.0", "s7"])
        check("inconclusive", (i["verdict"], i["exit"], i["max_closures_per_label"]), ("inconclusive", 2, 1))
        i2 = run(tags=["v1.0", "m6"], strict=True)
        check("inconclusive before incomplete", i2["verdict"], "inconclusive")
        # clean
        c = run(tags=["v1.0", "r2"])
        check("clean", (c["verdict"], c["exit"]), ("clean", 0))
        c2r = run(tags=["v1.0", "r2", "e3"])
        check("clean without --strict", c2r["verdict"], "clean")
        inc = run(tags=["v1.0", "r2", "e3"], strict=True)
        check("incomplete (empty)", (inc["verdict"], inc["exit"]), ("incomplete", 2))
        inc2 = run(tags=["v1.0", "r2", "n5"], strict=True)
        check("incomplete (without label)", (inc2["verdict"], inc2["exit"]), ("incomplete", 2))
        # Amendment 2 row: compared (2) < empty (1) + without label (2) -> incomplete, no --strict
        am = run(tags=["v1.0", "r2", "e3", "n5", "m6"])
        check("A2 incomplete compared<empty+nolabel",
              (am["verdict"], am["exit"], am["publication_points_compared"],
               am["points_with_empty_closure"], am["points_without_label"]),
              ("incomplete", 2, 2, 1, 2))
        # boundary: compared (2) == empty (1) + without label (1) -> clean
        bd = run(tags=["v1.0", "r2", "e3", "n5"])
        check("A2 boundary compared==empty+nolabel -> clean",
              (bd["verdict"], bd["exit"], bd["publication_points_compared"],
               bd["points_with_empty_closure"], bd["points_without_label"]),
              ("clean", 0, 2, 1, 1))
        # boundary with --strict is still incomplete via the strict row
        bds = run(tags=["v1.0", "r2", "e3", "n5"], strict=True)
        check("A2 boundary with --strict", bds["verdict"], "incomplete")
        # compared (2) < without label (3), no empty -> incomplete
        am2 = run(tags=["v1.0", "r2", "n5", "m6", "x8"])
        check("A2 incomplete only without-label", (am2["verdict"], am2["exit"]), ("incomplete", 2))
        # drift still wins over the new row
        am3 = run(tags=["v1.0", "v1.0-again", "e3", "n5", "m6", "x8"])
        check("A2 drift before new row", am3["verdict"], "drift")
        # no points
        z = run(tags=["zzz"])
        check("no_publication_points (filtered)", (z["verdict"], z["exit"], z["tags_filtered_out"],
                                                   z["points_not_commits"]),
              ("no_publication_points", 2, 9, 3))
        repo0 = os.path.join(tmp, "empty.git")
        _build_repo(repo0, [("c1", c1)])
        z0 = full_run(repo0, "VERSION", RX)
        check("no_publication_points (no tags)", (z0["verdict"], z0["exit"]), ("no_publication_points", 2))
        # only a tag at a blob
        _sh(["-C", repo0, "update-ref", "refs/tags/b", _sh(["-C", repo0, "hash-object", "-w", "--stdin"],
                                                           stdin=b"x").strip().decode()])
        z1 = full_run(repo0, "VERSION", RX)
        check("points_not_commits with tag at blob", (z1["verdict"], z1["points_not_commits"]),
              ("no_publication_points", 1))

        # --closure narrows: with *.txt both c1 and c3 differ -> 1.0 vs 2.0 distinct closures, clean
        t = run(tags=["v1.0", "r2"], closure=["*.txt"])
        check("--closure *.txt clean", (t["verdict"], t["points"]["v1.0"]["files"]), ("clean", 1))
        # Amendment 3: file-name exclusions
        for pth, exp in (("src/x_test.d/real.py", False), ("src/foo_test.py", True),
                         ("a/b.test.utils/c.js", False), ("x.md/run.py", False),
                         ("README.md", True), ("docs/a.py", True), ("tests/a.py", True),
                         ("lib/x_test.go", True), ("x_test.py", True), ("a/b.test.js", True),
                         ("a/b/c.md", True), ("a.md/b", False), ("src/tests/t.py", True),
                         ("src/a.py", False), ("node_modules/x.js", True), ("a/.git/x", True),
                         ("_test.", True), ("a_test", False)):
            check("A3 excluded(%r)" % pth, excluded(pth), exp)
        a3 = {b"src/x_test.d/real.py": ("100644", b"r\n"), b"src/foo_test.py": ("100644", b"f\n"),
              b"a/b.test.utils/c.js": ("100644", b"c\n"), b"x.md/run.py": ("100644", b"run\n"),
              b"README.md": ("100644", b"md\n"), b"docs/a.py": ("100644", b"d\n"),
              b"tests/a.py": ("100644", b"t\n")}
        repo3 = os.path.join(tmp, "a3.git")
        k3 = _build_repo(repo3, [("m", a3)])
        hm = [(b"a/b.test.utils/c.js", "blob", _blob_oid(b"c\n")),
              (b"src/x_test.d/real.py", "blob", _blob_oid(b"r\n")),
              (b"x.md/run.py", "blob", _blob_oid(b"run\n"))]
        check("A3 closure (default include)", closure_of(repo3, k3["m"]),
              dict(zip(("closure", "closure_id"), hand_ids(hm)), files=3))
        check("A3 closure (include *)", closure_of(repo3, "m", ["*"]),
              dict(zip(("closure", "closure_id"), hand_ids(hm)), files=3))
        # Amendment 2: named-group labels, the four examples, through a repository
        NRX = r"^V=(?P<a>[^|\n]*)\|(?P<b>[^|\n]*)\|(?P<c>[^|\n]*)\|(?P<d>[^|\n]*)$"
        nv = [("k1", b"V=6|1|0|\n"), ("k2", b"V=6|1|0|-rc1\n"), ("k3", b"V=6|+local||\n"),
              ("k4", b"V=|||\n"), ("k5", b"V=|1|0|\n"), ("k6", b"V=+x|1||\n"),
              ("k7", b"V=6|1|0|\n")]
        repo2 = os.path.join(tmp, "named.git")
        km = _build_repo(repo2, [(k, {b"a.py": ("100644", k.encode()), b"VERSION": ("100644", v)})
                                 for k, v in nv])
        for k in km:
            _sh(["-C", repo2, "update-ref", "refs/tags/t" + k, km[k]])
        nr = full_run(repo2, "VERSION", NRX)
        got = dict((k, nr["points"]["t" + k]["label"]) for k in km)
        check("A2 named labels", got, {"k1": "6.1.0", "k2": "6.1.0-rc1", "k3": "6+local", "k4": None,
                                       "k5": "1.0", "k6": "+x.1", "k7": "6.1.0"})
        check("A2 named labels verdict", (nr["verdict"], nr["drifting"].keys() == {"6.1.0"}),
              ("drift", True))
        # direct, by hand, on the regex engine
        L = lambda pat, text: label_from_match(re.search(pat, text, re.MULTILINE))
        check("A2 ex 6,1,0", L(r"(?P<x>\d+)\.(?P<y>\d+)\.(?P<z>\d+)", "6.1.0"), "6.1.0")
        check("A2 ex 6,1,0,-rc1", L(r"(?P<x>\d+)\.(?P<y>\d+)\.(?P<z>\d+)(?P<p>\S*)", "6.1.0-rc1"),
              "6.1.0-rc1")
        check("A2 ex 6,1,0,''", L(r"(?P<x>\d+)\.(?P<y>\d+)\.(?P<z>\d+)(?P<p>\S*)", "6.1.0"), "6.1.0")
        check("A2 ex 6,+local", L(r"(?P<x>\d+)(?P<p>\S*)", "6+local"), "6+local")
        check("A2 order by group number not name", L(r"(?P<z>\d)(?P<a>\d)", "98"), "9.8")
        check("A2 None skipped", L(r"(?P<a>\d+)(?:-(?P<b>x))?", "7"), "7")
        check("A2 unnamed groups ignored", L(r"(\w+)-(?P<n>\d+)", "abc-5"), "5")
        check("A2 all empty -> no label", L(r"v(?P<a>\d*)(?P<b>\d*)", "v"), None)
        check("no named groups: group 1", L(r"v(\d+)(\d)", "v123"), "12")
        # symlink-only and gitlink-only closures are members
        s = closure_of(repo, "c1", ["link.py"])
        check("symlink member", s, dict(zip(("closure", "closure_id"),
                                            hand_ids([(b"link.py", "blob", _blob_oid(b"src/a.py"))])),
                                        files=1))
        gl = closure_of(repo, "c1", ["lib/sub"])
        check("gitlink member", gl, dict(zip(("closure", "closure_id"),
                                             hand_ids([(b"lib/sub", "commit", gitlink.decode())])),
                                         files=1))
        nu = closure_of(repo, "c1", [b"src/\xff.py".decode("utf-8", "surrogateescape")])
        check("non-UTF-8 path member", nu["files"], 1)

        # compare
        cp = compare(repo, "v1.0", "v1.0-again")
        check("compare changed", (cp["changed"], cp["only_in_a"], cp["only_in_b"]),
              (["src/a.py"], [], []))
        check("compare a/b", (cp["a"]["commit"], cp["a"]["closure_id"], cp["b"]["commit"], cp["b"]["closure"]),
              (cm["c1"], f1, cm["c2"], s2))
        cp2 = compare(repo, "v1.0", "e3")
        check("compare only_in_a sorted as str",
              (cp2["only_in_a"], cp2["only_in_b"], cp2["changed"], cp2["b"]["files"]),
              (["lib/sub", "link.py", "main.go", "src/a.py", "src/\udcff.py"], [], [], 0))
        cp3 = compare(repo, "c3", cm["c7"])  # branch name and raw oid as revisions
        check("compare revisions", (cp3["a"]["commit"], cp3["changed"]), (cm["c3"], []))
        # tag name wins over a branch of the same name
        _sh(["-C", repo, "update-ref", "refs/tags/c5", cm["c1"]])
        cp4 = compare(repo, "c5", "c5")
        check("compare tag before branch", cp4["a"]["commit"], cm["c1"])
        # json with surrogate-escaped path
        check("JSON of surrogate path", "src/\\udcff.py" in json.dumps(cp2), True)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    bad = [n for n, ok in results if not ok]
    print("self-test: %d checks, %d passed, %d failed" % (len(results), len(results) - len(bad), len(bad)))
    return 0 if not bad else 1


# ---------------------------------------------------------------------------
# Command line

def main(argv=None):
    ap = argparse.ArgumentParser(prog="oracle.py")
    ap.add_argument("repo", nargs="?")
    ap.add_argument("--version-file")
    ap.add_argument("--version-regex")
    ap.add_argument("--closure", action="append", default=None)
    ap.add_argument("--tags", action="append", default=None)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"))
    ap.add_argument("--self-test", action="store_true")
    ns = ap.parse_args(argv)
    if ns.self_test:
        return self_test()
    if not ns.repo:
        ap.error("REPO is required")
    try:
        if ns.compare:
            res = compare(ns.repo, ns.compare[0], ns.compare[1], closure=ns.closure)
        else:
            if ns.version_file is None or ns.version_regex is None:
                ap.error("--version-file and --version-regex are required")
            res = full_run(ns.repo, ns.version_file, ns.version_regex, closure=ns.closure,
                           tags=ns.tags, strict=ns.strict)
    except GitError as e:
        sys.stderr.write("oracle: %s\n" % e)
        return 3
    except re.error as e:
        sys.stderr.write("oracle: bad --version-regex: %s\n" % e)
        return 3
    sys.stdout.write(json.dumps(res) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
