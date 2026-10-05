#!/usr/bin/env python3
"""Properties of closure_drift, on generated repositories, against an independent oracle.

What is tested and why is in tests/PREREGISTRATION_PROPERTIES.md, written before this file.

    python3 tests/properties.py                  # 17 properties over seeds 0..59
    python3 tests/properties.py --controls       # each broken detector must turn its property red
    python3 tests/properties.py --seeds 5 --only PR06
    python3 tests/properties.py --write-expected # (maintainer) rewrite properties_expected.json from the oracle

Exit 0 when no property is red beyond the closed list KNOWN_OPEN, 1 otherwise. Zero dependencies.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import fnmatch
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import oracle  # noqa: E402 — written from tests/ORACLE_SPEC.md by someone who did not read the detector

DETECTOR = HERE.parent / "closure_drift.py"
EXPECTED = HERE / "properties_expected.json"
VFILE = "version.cfg"
VREGEX = r'(?<![\w-])"?version"?\s*[:=]\s*["\']([^"\']+)["\']'
SEEDS = 60

# A red property listed here is a known, published failure: (property, sys.platform) -> where it
# is written up. The list is closed; a red anywhere else fails the run.
KNOWN_OPEN: dict = {}

DIRS = ["src", "lib", "app", "Lib", "SRC", "pkg", "core", "tests", "test", "docs", "vendor",
        "node_modules", "spec", "a b", "ação", "x[1]", "util"]
FILES = [b"main.py", b"a.PY", b"mod.js", b"x.ts", b"lib.rs", b"m.go", b"J.java", b"readme.md",
         b"NOTES.MD", b"data.txt", b"foo_test.py", b"bar.test.js", b"c.c", b"Makefile",
         b"tab\there.py", b"line\nbreak.py", b"byte\xff.py", b"star*.py", b"q?.js", b"sp ace.py",
         "é.py".encode()]
GLOBS = ["src/**", "*.py", "**/*.c", "pkg/*", "?ib/**", "[a-s]rc/**", "**/core/**", "a b/**", "*",
         "Lib/**", "*.PY", "**/util/*.js"]
LABELS = ["1.0.0", "1.0.1", "1.1.0", "2.0.0", "2.0"]
TAG_GLOBS = ["v*", "*1*", "r*", "py-*"]
OUTSIDE = [b"docs/extra.txt", b"deep/tests/t.py", b"zz-notes.md", b"node_modules/m.js"]


# ---------------------------------------------------------------- the model and its repository

class Model:
    """commits: [{path bytes: (mode, payload)}]; a payload is file content, or for mode 160000 a
    40-hex object id. tags: [[name, commit index or 'blob', date, annotated]]."""

    def __init__(self):
        self.commits: list[dict] = []
        self.tags: list[list] = []
        self.closure: list[str] | None = None
        self.late: list[tuple] = []      # (tree, tag name): written with plumbing after the import

    def copy(self) -> "Model":
        return copy.deepcopy(self)


def version_text(label: str | None) -> bytes:
    return b"name = x\n" if label is None else ('version = "%s"\n' % label).encode()


def generate(seed: int) -> Model:
    rng = random.Random(seed)
    m = Model()
    if rng.random() < 0.5:
        m.closure = rng.sample(GLOBS, rng.randint(1, 3))
    tree: dict = {}

    def free(path: bytes) -> bool:
        parts = path.split(b"/")
        if any(b"/".join(parts[:i]) in tree for i in range(1, len(parts))):
            return False
        return not any(p.startswith(path + b"/") for p in tree) and path not in tree

    def new_path() -> bytes:
        for _ in range(50):
            dirs = [rng.choice(DIRS).encode() for _ in range(rng.randint(0, 3))]
            path = b"/".join(dirs + [rng.choice(FILES)])
            if free(path):
                return path
        return b"src/f%d.py" % rng.randrange(10 ** 6)

    def content() -> bytes:
        return b"x = %d\n" % rng.randrange(10 ** 9)

    def entry():
        roll = rng.random()
        if roll < 0.05:
            return ("160000", ("%040x" % rng.getrandbits(160)).encode())
        if roll < 0.10:
            return ("120000", b"target-%d" % rng.randrange(99))
        return ("100755" if roll < 0.2 else "100644", content())

    for _ in range(rng.randint(5, 40)):
        tree[new_path()] = entry()
    label = rng.choice(LABELS)
    n_tags = rng.randint(2, 8)
    names = set()
    for i in range(n_tags):
        if i and rng.random() < 0.55:
            for _ in range(rng.randint(1, 3)):
                op = rng.random()
                if op < 0.5 and tree:
                    p = rng.choice(sorted(tree))
                    tree[p] = (tree[p][0] if tree[p][0] != "160000" else "100644", content())
                elif op < 0.75:
                    tree[new_path()] = entry()
                elif op < 0.9 and len(tree) > 3:
                    del tree[rng.choice(sorted(tree))]
                elif tree:
                    p = rng.choice(sorted(tree))
                    if tree[p][0] in ("100644", "100755"):
                        tree[p] = ("100755" if tree[p][0] == "100644" else "100644", tree[p][1])
        if i and rng.random() < 0.5:
            label = rng.choice(LABELS)
        snapshot = dict(tree)
        roll = rng.random()
        if roll < 0.85:
            snapshot[VFILE.encode()] = ("100644", version_text(label))
        elif roll < 0.93:
            snapshot[VFILE.encode()] = ("100644", version_text(None))
        m.commits.append(snapshot)
        while True:
            name = rng.choice(["v%d.%d.%d", "rel-%d.%d.%d", "py-%d.%d.%d", "versão-%d.%d.%d"]) % (
                rng.randint(0, 3), rng.randint(0, 9), rng.randint(0, 9))
            if name not in names:
                names.add(name)
                break
        m.tags.append([name, len(m.commits) - 1, 1_600_000_000 + 86_400 * i + rng.randrange(3600),
                       rng.random() < 0.5])
        if rng.random() < 0.3:               # a commit between tags
            tree[new_path()] = entry()
            extra = dict(tree)
            extra[VFILE.encode()] = ("100644", version_text(label))
            m.commits.append(extra)
    if rng.random() < 0.1:
        m.tags.append(["points-at-a-blob", "blob", 1_700_000_000, False])
    return m


def quoted(path: bytes) -> bytes:
    out = bytearray(b'"')
    for b in path:
        if b in (0x22, 0x5c):
            out += b"\\" + bytes([b])
        elif b < 0x20 or b >= 0x7f:
            out += b"\\%03o" % b
        else:
            out.append(b)
    return bytes(out) + b'"'


def build(m: Model, where: str) -> str:
    """Write the model as a bare repository with git fast-import. No working tree is involved."""
    subprocess.run(["git", "init", "--quiet", "--bare", "--initial-branch=main", where], check=True,
                   capture_output=True)
    s, marks, mark = bytearray(), {}, 0

    def blob(data: bytes) -> int:
        nonlocal mark
        if data not in marks:
            mark += 1
            marks[data] = mark
            s.extend(b"blob\nmark :%d\ndata %d\n" % (mark, len(data)) + data + b"\n")
        return marks[data]

    commit_marks = []
    for i, tree in enumerate(m.commits):
        files = [(p, mode, payload if mode == "160000" else blob(payload)) for p, (mode, payload) in tree.items()]
        mark += 1
        commit_marks.append(mark)
        when = b"%d +0000" % (1_500_000_000 + 1000 * i)
        s.extend(b"commit refs/heads/main\nmark :%d\nauthor A <a@example.org> %s\n"
                 b"committer A <a@example.org> %s\ndata 2\nc\n\n" % (mark, when, when))
        if i:
            s.extend(b"from :%d\n" % commit_marks[i - 1])
        s.extend(b"deleteall\n")
        for p, mode, ref in files:
            s.extend(b"M " + mode.encode() + b" " + (ref if mode == "160000" else b":%d" % ref)
                     + b" " + quoted(p) + b"\n")
        s.extend(b"\n")
    blob_tags = []
    for name, target, date, annotated in m.tags:
        if target == "blob":
            blob_tags.append(name)
        elif annotated:
            s.extend(b"tag " + name.encode() + b"\nfrom :%d\ntagger T <t@example.org> %d +0000\ndata 0\n\n"
                     % (commit_marks[target], date))
        else:
            s.extend(b"reset refs/tags/" + name.encode() + b"\nfrom :%d\n\n" % commit_marks[target])
    # core.ignorecase is set by `git init` on macOS and Windows; with it fast-import files `Lib/x`
    # under an existing `lib/`, and the repository would differ from one platform to the next
    r = subprocess.run(["git", "-C", where, "-c", "core.ignorecase=false", "-c", "core.precomposeunicode=false",
                        "fast-import", "--quiet", "--date-format=raw"], input=bytes(s),
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("git fast-import failed: " + r.stderr.decode("utf-8", "replace")[:300])
    for name in blob_tags:
        oid = subprocess.run(["git", "-C", where, "hash-object", "-w", "--stdin"], input=b"not a commit\n",
                             capture_output=True, check=True).stdout.decode().strip()
        subprocess.run(["git", "-C", where, "update-ref", "refs/tags/" + name, oid], check=True,
                       capture_output=True)
    for n, (tree, name) in enumerate(m.late):
        # fast-import refuses a submodule pointer whose id names a blob; the index does not
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(where, f"late-{n}.index"),
                   GIT_AUTHOR_NAME="A", GIT_AUTHOR_EMAIL="a@example.org", GIT_COMMITTER_NAME="A",
                   GIT_COMMITTER_EMAIL="a@example.org", GIT_AUTHOR_DATE="1950000000 +0000",
                   GIT_COMMITTER_DATE="1950000000 +0000")
        lines = b"".join(mode.encode() + b" " + (payload if mode == "160000" else blob_id(payload))
                         + b"\t" + p + b"\0" for p, (mode, payload) in tree.items())
        g = ["git", "-C", where, "-c", "core.ignorecase=false", "-c", "core.precomposeunicode=false"]
        subprocess.run(g + ["update-index", "-z", "--index-info"], input=lines, env=env, check=True,
                       capture_output=True)
        tree_id = subprocess.run(g + ["write-tree", "--missing-ok"], env=env, check=True,
                                 capture_output=True).stdout.decode().strip()
        commit = subprocess.run(g + ["commit-tree", tree_id, "-p", "refs/heads/main", "-m", "late"], env=env,
                                check=True, capture_output=True).stdout.decode().strip()
        subprocess.run(g + ["update-ref", "refs/tags/" + name, commit], check=True, capture_output=True)
        os.unlink(env["GIT_INDEX_FILE"])
    return where


def blob_id(data: bytes) -> bytes:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest().encode()


# ---------------------------------------------------------------- running the detector

class Runs:
    """Every detector run of the suite, for PR13."""

    def __init__(self, detector: Path):
        self.detector = detector
        self.broken: list[str] = []

    def __call__(self, repo: str, *args: str, closure=None, base=True, cwd=None):
        cmd = [sys.executable, str(self.detector), repo, "--json"]
        if base:
            cmd += ["--max-commits", "1000000", "--version-file", VFILE, "--version-regex", VREGEX]
        for g in closure or []:
            cmd += ["--closure", g]
        r = subprocess.run(cmd + list(args), capture_output=True, stdin=subprocess.DEVNULL, cwd=cwd)
        err = r.stderr.decode("utf-8", "replace")
        try:
            report = json.loads(r.stdout.decode("utf-8"))
        except ValueError:
            report = None
        verdict = report.get("verdict") if isinstance(report, dict) else None
        zero = ("clean", "would_be_clean", "identical", "differs_under_two_labels")
        one = ("drift", "would_drift", "differs_under_one_label")
        if (r.returncode not in (0, 1, 2) or (r.returncode == 0) != (verdict in zero)
                or (r.returncode == 1) != (verdict in one) or "Traceback" in err or "internal error" in err):
            self.broken.append(f"exit {r.returncode}, verdict {verdict!r}, stderr {err.strip()[:120]!r}, "
                               f"args {' '.join(args)!r}")
        return r.returncode, report, r.stdout


def essence(report: dict) -> dict:
    """What must not change when tags are renamed or re-dated: verdict, counts, and for each label
    in drift the set of full closure ids."""
    if report is None or "labels" not in report:
        return {"verdict": report and report.get("verdict")}
    ids = report["closure_ids"]
    keep = ("verdict", "labels", "labels_covering_multiple_closures", "max_closures_per_label",
            "publication_points_scanned", "publication_points_compared", "points_without_label",
            "points_with_empty_closure", "points_not_commits")
    out = {k: report[k] for k in keep}
    out["drift"] = {label: sorted(ids[key] for key in keys) for label, keys in report["drift"].items()}
    return out


def without(report, *fields):
    r = copy.deepcopy(report)
    for f in fields:
        if "." in f:
            a, b = f.split(".")
            r.get(a, {}).pop(b, None)
        else:
            r.pop(f, None)
    return r


class Case:
    """One seed: its model, its repository, and a place to build variants."""

    def __init__(self, seed: int, tmp: str, run: Runs):
        self.seed, self.tmp, self.run, self.n = seed, tmp, run, 0
        self.model = generate(seed)
        self.repo = build(self.model, os.path.join(tmp, "base.git"))
        self.closure = self.model.closure
        self._base = None

    def variant(self, model: Model) -> str:
        self.n += 1
        return build(model, os.path.join(self.tmp, f"v{self.n}.git"))

    def base(self):
        if self._base is None:
            self._base = self.run(self.repo, closure=self.closure)
        return self._base

    def commit_tags(self):
        return [t for t in self.model.tags if t[1] != "blob"]

    def members(self, model: Model, repo: str, tag: str) -> list[str]:
        """The closure members at a tag, as the detector lists them against a commit with none."""
        aux = model.copy()
        aux.commits.append({b"docs/aux.md": ("100644", b"x\n")})
        aux.tags.append(["zz-aux", len(aux.commits) - 1, 1_900_000_000, True])
        _c, rep, _o = self.run(self.variant(aux), "--compare", tag, "zz-aux", closure=self.closure)
        return rep["only_in_a"] if rep and "only_in_a" in rep else []


# ---------------------------------------------------------------- the properties
# Each returns None (holds), a string (red, with the detail), or SKIP (nothing to test in this seed).

SKIP = object()
ERROR = "could not be evaluated"       # red in the suite; in a control it is not a catch


def oracle_run(c: Case, repo=None, **kw):
    return oracle.full_run(repo or c.repo, VFILE, VREGEX, closure=c.closure, **kw)


def agree_full(det: dict, orc: dict) -> str | None:
    if det is None:
        return "the detector printed no report"
    if orc["verdict"] == "no_publication_points" or det.get("verdict") == "no_publication_points":
        return None if det.get("verdict") == orc["verdict"] else f"verdict {det.get('verdict')} vs oracle {orc['verdict']}"
    for k in ("verdict", "labels", "labels_covering_multiple_closures", "max_closures_per_label",
              "publication_points_scanned", "publication_points_compared", "points_without_label",
              "points_with_empty_closure", "points_not_commits"):
        theirs = len(orc[k]) if k == "labels" else orc.get(k)
        if det.get(k) != theirs:
            return f"{k}: detector {det.get(k)!r}, oracle {theirs!r}"
    mine = essence(det)["drift"]
    theirs = {k: sorted(v) for k, v in orc["drifting"].items()}
    return None if mine == theirs else f"labels in drift or their closure ids differ: {sorted(mine)} vs {sorted(theirs)}"


def pr01(c: Case):
    code, det, _ = c.base()
    orc = oracle_run(c)
    bad = agree_full(det, orc)
    if bad is None and code != orc["exit"]:
        bad = f"exit {code}, oracle {orc['exit']}"
    return bad


def pr02(c: Case):
    tags = c.commit_tags()
    rng = random.Random(c.seed * 7 + 1)
    a, b = rng.choice(tags)[0], rng.choice(tags)[0]
    _code, det, _ = c.run(c.repo, "--compare", a, b, closure=c.closure)
    orc = oracle.compare(c.repo, a, b, closure=c.closure)
    if det is None or "a" not in det:
        return "the detector printed no comparison"
    for side in "ab":
        if det[side]["files"] != orc[side]["files"]:
            return f"files of {side}: {det[side]['files']} vs oracle {orc[side]['files']}"
        if det[side]["files"] and det[side]["closure_id"] != orc[side]["closure_id"]:
            return f"closure id of {side} differs from the oracle's"
    for k in ("changed", "only_in_a", "only_in_b"):
        if det[k] != orc[k]:
            return f"{k}: {det[k][:3]!r} vs oracle {orc[k][:3]!r}"
    return None


def pr03(c: Case):
    code1, _r, out1 = c.base()
    code2, _r, out2 = c.run(c.repo, closure=c.closure)
    return None if (code1, out1) == (code2, out2) else "two runs printed different bytes or ended differently"


def pr04(c: Case):
    copy_ = os.path.join(c.tmp, "clone.git")
    subprocess.run(["git", "clone", "--quiet", "--bare", c.repo, copy_], check=True, capture_output=True)
    _c1, one, _ = c.base()
    _c2, two, _ = c.run(copy_, closure=c.closure)
    return None if without(one, "repo") == without(two, "repo") else "the clone gives a different report"


def pr05(c: Case):
    m = c.model.copy()
    for i, tree in enumerate(m.commits):
        for p in OUTSIDE:
            if i % 3 != 2 and not any(q == p or q.startswith(p + b"/") or p.startswith(q + b"/") for q in tree):
                tree[p] = ("100644", b"outside %d\n" % i)
    _c1, one, _ = c.base()
    _c2, two, _ = c.run(c.variant(m), closure=c.closure)
    drop = ("repo", "stamp.measured_at_head")
    return None if without(one, *drop) == without(two, *drop) else "files outside the closure changed the report"


def one_member_changed(c: Case, how: str):
    """→ (model with one more tag `zz-new` under an undrifted label, label, path, base report) or SKIP."""
    _code, base, _ = c.base()
    if not base or "drift" not in base:
        return SKIP
    rng = random.Random(c.seed * 13 + len(how))
    label_of = {}
    for name, idx, _d, _a in c.commit_tags():
        text = c.model.commits[idx].get(VFILE.encode(), ("", b""))[1]
        if text.startswith(b'version = "'):
            label_of[name] = text.split(b'"')[1].decode()
    candidates = [(n, l) for n, l in sorted(label_of.items()) if l not in base["drift"]]
    rng.shuffle(candidates)
    for name, label in candidates:
        idx = next(t[1] for t in c.model.tags if t[0] == name)
        members = c.members(c.model, c.repo, name)
        tree = dict(c.model.commits[idx])
        by_text = {p.decode("utf-8", "surrogateescape"): p for p in tree}
        plain = [p for p in members if tree[by_text[p]][0] in ("100644", "100755") and p != VFILE]
        if how == "removed" and len(members) < 2 or not plain:
            continue
        path = rng.choice(plain)
        raw = by_text[path]
        mode, payload = tree[raw]
        if how == "changed":
            tree[raw] = (mode, payload + b"# changed\n")
        elif how == "removed":
            del tree[raw]
        elif how == "kind":
            tree[raw] = ("160000", blob_id(payload))
        elif how == "mode":
            tree[raw] = ("100755" if mode == "100644" else "100644", payload)
        elif how == "added":
            head, _, tail = raw.rpartition(b"/")
            stem, dot, ext = tail.rpartition(b".")
            new = (head + b"/" if head else b"") + (stem + b"_new." + ext if dot else tail + b"_new")
            if new in tree:
                continue
            tree[new] = ("100644", b"added\n")
            path = new.decode("utf-8", "surrogateescape")
        m = c.model.copy()
        if how == "kind":
            m.late.append((tree, "zz-new"))
        else:
            m.commits.append(tree)
            m.tags.append(["zz-new", len(m.commits) - 1, 1_950_000_000, True])
        return m, label, path, base
    return SKIP


def pr06(c: Case):
    tested = 0
    for how, where in (("changed", "changed"), ("removed", "only_in_first"), ("added", "only_in_other"),
                       ("kind", "changed")):
        got = one_member_changed(c, how)
        if got is SKIP:
            continue
        m, label, path, _base = got
        tested += 1
        _code, rep, _ = c.run(c.variant(m), "--explain", label, closure=c.closure)
        if not rep or rep.get("verdict") != "drift" or label not in rep.get("drift", {}):
            return f"{how}: one member {path!r} differs under {label} and the verdict is {rep and rep.get('verdict')}"
        others = rep.get("explain", {}).get("others", [])
        want = {"changed": [], "only_in_first": [], "only_in_other": []}
        want[where] = [path]
        if len(others) != 1 or {k: others[0][k] for k in want} != want:
            return f"{how}: --explain does not name exactly {path!r}"
    return None if tested else SKIP


def pr07(c: Case):
    got = one_member_changed(c, "mode")
    if got is SKIP:
        return SKIP
    m, label, path, base = got
    _code, rep, _ = c.run(c.variant(m), closure=c.closure)
    if label in rep.get("drift", {}):
        return f"a change of mode alone on {path!r} was reported as drift under {label}"
    return None


def pr08(c: Case):
    m = c.model.copy()
    rng = random.Random(c.seed * 17 + 3)
    dates = [1_800_000_000 + 1000 * i for i in range(len(m.tags))]
    rng.shuffle(dates)
    for t, d in zip(m.tags, dates):
        t[2], t[3] = d, t[1] != "blob"
    _c1, one, _ = c.base()
    _c2, two, _ = c.run(c.variant(m), closure=c.closure)
    return None if essence(one) == essence(two) else "another creation order of the tags changes the result"


def pr09(c: Case):
    m = c.model.copy()
    for i, t in enumerate(m.tags):
        t[0] = f"renamed/{i}-x"
    _c1, one, _ = c.base()
    _c2, two, _ = c.run(c.variant(m), closure=c.closure)
    return None if essence(one) == essence(two) else "renaming the tags changes the result"


def pr10(c: Case):
    tags = c.commit_tags()
    rng = random.Random(c.seed * 19 + 5)
    a, b = rng.choice(tags)[0], rng.choice(tags)[0]
    _c, ab, _ = c.run(c.repo, "--compare", a, b, closure=c.closure)
    _c, ba, _ = c.run(c.repo, "--compare", b, a, closure=c.closure)
    _c, aa, _ = c.run(c.repo, "--compare", a, a, closure=c.closure)
    if not ab or not ba or "a" not in ab or "a" not in ba:
        return "no comparison printed"
    if (ab["verdict"], ab["changed"], ab["only_in_a"], ab["only_in_b"]) != \
            (ba["verdict"], ba["changed"], ba["only_in_b"], ba["only_in_a"]):
        return f"--compare {a} {b} and its reverse disagree"
    if aa["a"]["files"] and aa["verdict"] != "identical":
        return f"--compare {a} {a} is {aa['verdict']}"
    return None


def pr11(c: Case):
    tags = c.commit_tags()
    m = c.model.copy()
    victim = random.Random(c.seed * 23 + 7).choice(tags)[0]
    m.tags = [t for t in m.tags if t[0] != victim]
    _c1, one, _ = c.base()
    _c2, two, _ = c.run(c.variant(m), closure=c.closure)
    more = set((two or {}).get("drift", {})) - set((one or {}).get("drift", {}))
    return f"removing the tag {victim} put {sorted(more)} in drift" if more else None


def pr12(c: Case):
    _code, wt, _ = c.run(c.repo, "--would-tag", closure=c.closure)
    if not wt or wt.get("verdict") not in ("would_drift", "would_be_clean"):
        return SKIP
    m = c.model.copy()
    m.tags.append(["zz-head", len(m.commits) - 1, 1_960_000_000, True])
    _code, after, _ = c.run(c.variant(m), closure=c.closure)
    in_drift = wt["label_at_head"] in (after or {}).get("drift", {})
    if in_drift != (wt["verdict"] == "would_drift"):
        return (f"--would-tag said {wt['verdict']} for label {wt['label_at_head']}; after tagging HEAD "
                f"that label is {'in' if in_drift else 'not in'} drift")
    return None


def pr14(c: Case):
    _c1, one, _ = c.base()
    _c2, rel, _ = c.run("base.git", closure=c.closure, cwd=c.tmp)
    _c3, slash, _ = c.run(c.repo + os.sep, closure=c.closure)
    if without(one, "repo") != without(rel, "repo"):
        return "a relative path gives a different report"
    return None if without(one, "repo") == without(slash, "repo") else "a trailing separator gives a different report"


def fingerprint(c: Case) -> dict:
    """Commit ids and the oracle's closure ids per tag, under the default closure and the seed's."""
    out = {}
    for name, _i, _d, _a in c.commit_tags():
        sha = subprocess.run(["git", "-C", c.repo, "rev-parse", "refs/tags/" + name + "^{commit}"],
                             capture_output=True, check=True).stdout.decode().strip()
        row = {"commit": sha}
        for key, closure in (("default", None), ("seed", c.closure)):
            got = oracle.closure_of(c.repo, sha, closure=closure)
            row[key] = [got["closure_id"] if got["files"] else None, got["files"]]
        out[name] = row
    return out


def pr15(c: Case):
    if c.seed > 9:
        return SKIP
    try:
        expected = json.loads(EXPECTED.read_text(encoding="utf-8"))[str(c.seed)]
    except (OSError, KeyError, ValueError):
        return "tests/properties_expected.json has no entry for this seed"
    got = fingerprint(c)
    if got != expected:
        bad = next(n for n in expected if got.get(n) != expected[n])
        return f"the oracle differs from the recorded constants at tag {bad}"
    for name, row in expected.items():
        for key, closure in (("default", None), ("seed", c.closure)):
            _code, rep, _ = c.run(c.repo, "--compare", name, name, closure=closure)
            mine = [rep["a"]["closure_id"] if rep["a"]["files"] else None, rep["a"]["files"]]
            if mine != row[key]:
                return f"the detector differs from the recorded constants at tag {name} ({key} closure)"
    return None


def pr16(c: Case):
    _c1, base, _ = c.base()
    code, strict, _ = c.run(c.repo, "--strict", closure=c.closure)
    b, s = base.get("verdict"), strict.get("verdict")
    if not (s == b or (b == "clean" and s == "incomplete")):
        return f"--strict turned {b} into {s}"
    want = oracle_run(c, strict=True)          # added by amendment 1: K07 was not caught without it
    return None if (s, code) == (want["verdict"], want["exit"]) else \
        f"--strict gives {s} (exit {code}); the oracle gives {want['verdict']} (exit {want['exit']})"


def pr17(c: Case):
    glob = random.Random(c.seed * 29 + 11).choice(TAG_GLOBS)
    m = c.model.copy()
    m.tags = [t for t in m.tags if fnmatch.fnmatchcase(t[0], glob)]
    _c1, one, _ = c.run(c.repo, "--tags", glob, closure=c.closure)
    _c2, two, _ = c.run(c.variant(m), closure=c.closure)
    return None if essence(one) == essence(two) else f"--tags {glob} differs from the repository holding only those tags"


PROPERTIES = [("PR01", pr01), ("PR02", pr02), ("PR03", pr03), ("PR04", pr04), ("PR05", pr05),
              ("PR06", pr06), ("PR07", pr07), ("PR08", pr08), ("PR09", pr09), ("PR10", pr10),
              ("PR11", pr11), ("PR12", pr12), ("PR14", pr14), ("PR15", pr15), ("PR16", pr16),
              ("PR17", pr17)]


def one_seed(seed: int, detector: Path, only) -> dict:
    tmp = tempfile.mkdtemp(prefix="cd-prop-")
    run = Runs(detector)
    out = {}
    try:
        case = Case(seed, tmp, run)
        for pid, fn in PROPERTIES:
            if only and pid not in only and "PR13" not in only:
                continue
            try:
                out[pid] = fn(case)
            except Exception as e:  # noqa: BLE001 — a property that cannot be evaluated is red, with the cause
                out[pid] = f"{ERROR}: {type(e).__name__}: {str(e)[:160]}"
        if not only or "PR13" in only:
            out["PR13"] = run.broken[0] if run.broken else None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def suite(detector: Path, seeds, only=None, workers=4) -> dict:
    """→ {property: {"red": {seed: detail}, "tested": n}}"""
    table = {pid: {"red": {}, "tested": 0} for pid in [p for p, _ in PROPERTIES] + ["PR13"]
             if not only or pid in only}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for seed, result in zip(seeds, pool.map(lambda s: one_seed(s, detector, only), seeds)):
            for pid, r in result.items():
                if r is SKIP or pid not in table:
                    continue
                table[pid]["tested"] += 1
                if r is not None:
                    table[pid]["red"][seed] = r
    return table


CONTROLS = [
    ("K01", "`**/docs/**` removed from the exclusions", ("PR01", "PR05"),
     '"**/docs/**", ', ""),
    ("K02", "the full id leaves out the entry type", ("PR06",),
     'full.update(raw + b"\\0" + kind.encode() + b" " + oid.encode() + b"\\n")',
     'full.update(raw + b"\\0" + oid.encode() + b"\\n")'),
    ("K03", "paths are matched without regard to case", ("PR01", "PR15"),
     "            got = matches(path, self.include) and not matches(path, CLOSURE_EXCLUDE)",
     "            got = (matches(path.lower(), [g.lower() for g in self.include])\n"
     "                   and not matches(path.lower(), CLOSURE_EXCLUDE))"),
    ("K04", "`only_in_a` and `only_in_b` are exchanged in --compare", ("PR02", "PR10"),
     '"changed": changed, "only_in_a": only_a, "only_in_b": only_b})',
     '"changed": changed, "only_in_a": only_b, "only_in_b": only_a})'),
    ("K05", "--would-tag compares with the same closure instead of the different ones", ("PR12",),
     'by_label.get(label, {}).items() if f != full]', 'by_label.get(label, {}).items() if f == full]'),
    ("K06", "--tags keeps the tags that do not match", ("PR17",),
     "if tag_globs and not any(fnmatch.fnmatchcase(name, g) for g in tag_globs):",
     "if tag_globs and any(fnmatch.fnmatchcase(name, g) for g in tag_globs):"),
    ("K07", "--strict is ignored", ("PR16",),
     "elif labels.conflicts or (a.strict and (no_label or empty or truncated)):",
     "elif labels.conflicts:"),
    ("K08", "`inconclusive` exits 0", ("PR13",),
     'code = {"clean": 0, "drift": 1}.get(verdict, 2)',
     'code = {"clean": 0, "inconclusive": 0, "drift": 1}.get(verdict, 2)'),
    ("K09", "tags are scanned in name order and the first closure of a label wins", ("PR01", "PR08"),
     ('"--sort=creatordate",', "            if full not in states:\n"),
     ('"--sort=refname",', "            if not states:\n")),
    ("K10", "submodule pointers are left out of the closure", ("PR01",),
     'return [e for e in entries if e[1] in ("blob", "commit") and self.holds(e[0])]',
     'return [e for e in entries if e[1] == "blob" and self.holds(e[0])]'),
]


def controls(seeds) -> int:
    source = DETECTOR.read_text(encoding="utf-8")
    caught = 0
    tmp = tempfile.mkdtemp(prefix="cd-ctl-")
    try:
        for kid, what, must, old, new in CONTROLS:
            olds, news = ((old,), (new,)) if isinstance(old, str) else (old, new)
            if any(source.count(o) != 1 for o in olds):
                print(f"{kid}  NOT CAUGHT  the replacement does not apply: {what}")
                continue
            text = source
            for o, n in zip(olds, news):
                text = text.replace(o, n)
            mutant = Path(tmp) / f"{kid}.py"
            mutant.write_text(text, encoding="utf-8")
            table = suite(mutant, seeds, only=set(must))
            red = [p for p in must if any(not d.startswith(ERROR) for d in table[p]["red"].values())]
            if red:
                caught += 1
                print(f"{kid}  caught by {', '.join(red)}  ({what})")
            else:
                print(f"{kid}  NOT CAUGHT  {', '.join(must)} stayed green: {what}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(CONTROLS)} controls · {caught} caught · {len(CONTROLS) - caught} not caught")
    return 0 if caught == len(CONTROLS) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=SEEDS)
    ap.add_argument("--only", action="append")
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--write-expected", action="store_true")
    ap.add_argument("--detector", default=str(DETECTOR))
    a = ap.parse_args()
    seeds = list(range(a.seeds))

    if a.write_expected:
        out = {}
        for seed in range(10):
            tmp = tempfile.mkdtemp(prefix="cd-exp-")
            try:
                out[str(seed)] = fingerprint(Case(seed, tmp, Runs(DETECTOR)))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        EXPECTED.write_bytes((json.dumps(out, indent=1, sort_keys=True) + "\n").encode("utf-8"))
        print(f"wrote {EXPECTED.name} from the oracle, seeds 0-9")
        return 0
    if a.controls:
        return controls(seeds[:20])

    detector = Path(a.detector).resolve()
    print(f"detector  {detector.name}  sha256 {hashlib.sha256(detector.read_bytes()).hexdigest()[:16]}")
    print(f"oracle    sha256 {hashlib.sha256((HERE / 'oracle.py').read_bytes()).hexdigest()[:16]}")
    print(f"seeds     0..{a.seeds - 1}   platform {sys.platform}   python {sys.version.split()[0]}\n")
    table = suite(detector, seeds, only=set(a.only) if a.only else None)
    green = red = known = not_run = 0
    for pid in sorted(table):
        t = table[pid]
        if t["red"]:
            first = min(t["red"])
            where = KNOWN_OPEN.get((pid, sys.platform))
            if where:
                known += 1
                state = f"red, known and open ({where})"
            else:
                red += 1
                state = "RED"
            print(f"{pid}  {state}  {len(t['red'])} of {t['tested']} seeds, e.g. seed {first}: {t['red'][first]}")
        elif t["tested"] == 0:
            not_run += 1
            print(f"{pid}  not run  no seed offered a case")
        else:
            green += 1
            print(f"{pid}  green  {t['tested']} seeds")
    print(f"\n{len(table)} properties · {green} green · {red} red · {known} known and open · {not_run} not run")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
