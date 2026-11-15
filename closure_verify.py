#!/usr/bin/env python3
"""closure_verify — check the drift evidence of a closure_drift --json report, independently.

Written from docs/VERDICTS.md ("The closure, as a verifier must reproduce it") and tests/PREREGISTRATION.md
§37; it does not import or read closure_drift.py. Standard library only.

    python3 closure_verify.py REPORT.json                 # structural level
    python3 closure_verify.py REPORT.json --repo PATH     # structural and Git levels
    add --json for a machine-readable answer

Exit 0 verified at the level reached · 1 the report is contradicted · 2 cannot verify.
The last stderr line of a run that is not exit 0 is `reason: CODE`.
Trusted history (that this repository and its tags are the ones published) is never claimed.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys

__version__ = "1.11.0"

NEVER = ["**/test/**", "**/tests/**", "**/*_test.*", "**/*.test.*", "**/spec/**", "**/docs/**", "**/*.md",
         "**/node_modules/**", "**/vendor/**", "**/.git/**"]
NAMEABLE = {"test", "tests", "spec", "docs", "vendor", "node_modules"}
FILE_PATTERNS = [p[3:] for p in NEVER if p.startswith("**/") and "/" not in p[3:]]
FOLDER_PATTERNS = [p for p in NEVER if not (p.startswith("**/") and "/" not in p[3:])]

HEX16 = re.compile(r"[0-9a-f]{16}(~[0-9]+)?\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEXOID = re.compile(r"[0-9a-f]{40}\Z|[0-9a-f]{64}\Z")


class Stop(Exception):
    def __init__(self, exit_code, code, message):
        super().__init__(message)
        self.exit_code, self.code = exit_code, code


# ---- the closure definition -------------------------------------------------------------------------

def glob_hit(path, g):
    if fnmatch.fnmatchcase(path, g) or fnmatch.fnmatchcase(path, g.replace("**/", "*/")):
        return True
    if g.startswith("**/") and fnmatch.fnmatchcase(path, g[3:]):
        return True
    return g.endswith("/**") and path.startswith(g[:-2])


def is_member(path, is_file, include):
    if not any(glob_hit(path, g) for g in include):
        return False
    name = path.rsplit("/", 1)[-1]
    by_file = is_file and any(fnmatch.fnmatchcase(name, x) for x in FILE_PATTERNS)
    by_folder = any(glob_hit(path, p) for p in FOLDER_PATTERNS)
    if not by_file and not by_folder:
        return True
    if by_file:
        return False                                   # no glob brings back a file pattern
    folders = set(path.split("/")[:-1] if is_file else path.split("/"))
    if ".git" in folders:
        return False
    lying_in = folders & NAMEABLE
    if not lying_in:
        return False
    return any(lying_in <= (set(g.split("/")) & NAMEABLE) and glob_hit(path, g) for g in include)


def ids(entries, include, with_modes):
    short, full, n = hashlib.sha256(), hashlib.sha256(), 0
    for mode, kind, oid, raw in entries:
        if kind not in ("blob", "commit"):
            continue
        path = raw.decode("utf-8", "surrogateescape")
        if not is_member(path, kind == "blob", include):
            continue
        short.update(raw + oid.encode())
        tail = b" " + mode if with_modes else b""
        full.update(raw + b"\0" + kind.encode() + b" " + oid.encode() + tail + b"\n")
        n += 1
    return short.hexdigest()[:16], full.hexdigest(), n


# ---- structural level -------------------------------------------------------------------------------

def structural(r):
    def bad(msg):
        raise Stop(1, "report_inconsistent", msg)
    if not isinstance(r, dict):
        raise Stop(2, "report_unreadable", "the report is not a JSON object")
    if r.get("mode") is not None:
        raise Stop(2, "unsupported_report", f"a {r['mode']!r} report is not verified; only tags and commits scans")
    if r.get("report_format") != 2:
        raise Stop(2, "unsupported_report", f"report_format {r.get('report_format')!r} is not known here")
    for f in ("drift", "closure_ids", "closure_commits", "closure_globs", "verdict",
              "labels_covering_multiple_closures", "max_closures_per_label"):
        if f not in r:
            bad(f"the report has no {f}")
    drift, cids, ccom = r["drift"], r["closure_ids"], r["closure_commits"]
    if not all(isinstance(x, dict) for x in (drift, cids, ccom)) or not isinstance(r["closure_globs"], list):
        bad("drift, closure_ids and closure_commits must be objects, closure_globs a list")
    keys = []
    for label, cs in drift.items():
        if not isinstance(cs, dict) or len(cs) < 2:
            bad(f"label {label!r} is in drift with fewer than two closures")
        fulls = set()
        for k in cs:
            if not HEX16.match(k):
                bad(f"closure key {k!r} is not 16 hex")
            if k not in cids or k not in ccom:
                bad(f"closure {k} of {label!r} has no entry in closure_ids or closure_commits")
            if not isinstance(cids[k], str) or not HEX64.match(cids[k]):
                bad(f"closure id of {k} is not 64 hex")
            if not isinstance(ccom[k], str) or not HEXOID.match(ccom[k]):
                bad(f"commit of {k} is not a full object id")
            fulls.add(cids[k])
            keys.append((label, k))
        if len(fulls) != len(cs):
            bad(f"label {label!r} lists the same closure id twice")
    if set(cids) != {k for _l, k in keys} or set(ccom) != set(cids):
        bad("closure_ids or closure_commits name a closure that is not in drift")
    if r["labels_covering_multiple_closures"] != len(drift):
        bad("labels_covering_multiple_closures differs from the labels in drift")
    if r["max_closures_per_label"] != max([len(cs) for cs in drift.values()] or [r["max_closures_per_label"]]):
        bad("max_closures_per_label differs from the largest label in drift")
    if (r["verdict"] == "drift") != bool(drift):
        bad(f"verdict {r['verdict']!r} does not agree with drift")
    return keys


# ---- Git level --------------------------------------------------------------------------------------

class Repo:
    def __init__(self, path):
        self.path = path
        self.env = dict(os.environ, GIT_NO_REPLACE_OBJECTS="1", LC_ALL="C")
        if not os.path.isdir(path) or self.run("rev-parse", "--git-dir", ok=(0, 128)).strip() == "":
            raise Stop(2, "git_unreadable", f"{path} is not a git repository")
        self.fmt = self.run("rev-parse", "--show-object-format").strip() or "sha1"
        self.hashed = set()
        self.cat = subprocess.Popen(["git", "-C", path, "cat-file", "--batch"], stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, env=self.env)

    def run(self, *args, ok=(0,)):
        try:
            p = subprocess.run(["git", "-C", self.path, *args], capture_output=True, env=self.env)
        except OSError as e:
            raise Stop(2, "git_unreadable", f"git cannot run: {e}")
        if p.returncode not in ok:
            raise Stop(2, "git_unreadable", f"git {args[0]} failed: {p.stderr.decode(errors='replace').strip()}")
        return p.stdout.decode("utf-8", "surrogateescape")

    def history_is_original(self):
        if self.run("for-each-ref", "refs/replace").strip():
            raise Stop(2, "git_history_rewritten", "the repository has replace refs (refs/replace)")
        common = self.run("rev-parse", "--git-common-dir").strip()
        if os.path.exists(os.path.join(self.path, common, "info", "grafts")):
            raise Stop(2, "git_history_rewritten", "the repository has grafts (info/grafts)")
        if self.run("rev-parse", "--is-shallow-repository").strip() == "true":
            raise Stop(2, "git_history_rewritten", "the repository is shallow")

    def read(self, oid):
        self.cat.stdin.write(oid.encode() + b"\n")
        self.cat.stdin.flush()
        head = self.cat.stdout.readline().split()
        if len(head) == 2 and head[1] == b"missing":
            return None, None
        kind, size = head[1].decode(), int(head[2])
        body = self.cat.stdout.read(size)
        self.cat.stdout.read(1)
        return kind, body

    def check(self, oid, want):
        """Read an object, insist on its kind, and that its bytes hash to its name."""
        kind, body = self.read(oid)
        if kind is None:
            raise Stop(2, "object_missing", f"object {oid} is not in this repository")
        if kind != want:
            raise Stop(2, "object_missing", f"{oid} is a {kind}, not a {want}")
        if oid not in self.hashed:
            h = hashlib.new("sha256" if self.fmt == "sha256" else "sha1")
            h.update(f"{kind} {len(body)}\0".encode() + body)
            if h.hexdigest() != oid:
                raise Stop(2, "git_object_corrupt", f"{kind} {oid} does not hash to its name")
            self.hashed.add(oid)
        return body

    def tree_walk(self, tree):
        """Hash-check every tree under `tree`; return {path bytes: (mode, kind, oid)} for what it holds."""
        out, stack, width = {}, [(b"", tree)], 32 if self.fmt == "sha256" else 20
        while stack:
            prefix, t = stack.pop()
            body, i = self.check(t, "tree"), 0
            while i < len(body):
                sp = body.index(b" ", i)
                nul = body.index(b"\0", sp)
                mode, name = body[i:sp], body[sp + 1:nul]
                oid = body[nul + 1:nul + 1 + width].hex()
                i = nul + 1 + width
                path = prefix + name
                if mode == b"40000":
                    stack.append((path + b"/", oid))
                else:
                    out[path] = (mode, "commit" if mode == b"160000" else "blob", oid)
        return out

    def entries(self, commit):
        body = self.check(commit, "commit")
        tree = body.split(b"\n", 1)[0]
        if not tree.startswith(b"tree "):
            raise Stop(2, "git_object_corrupt", f"commit {commit} has no tree line")
        walked = self.tree_walk(tree[5:].decode())
        raw = subprocess.run(["git", "-C", self.path, "ls-tree", "-r", "-z", "--full-tree", commit],
                             capture_output=True, env=self.env)
        if raw.returncode:
            raise Stop(2, "git_unreadable", f"git ls-tree {commit} failed")
        out = []
        for rec in raw.stdout.split(b"\0"):
            if not rec:
                continue
            meta, path = rec.split(b"\t", 1)
            mode, kind, oid = meta.split(b" ")
            if walked.get(path) != (mode, kind.decode(), oid.decode()):
                raise Stop(2, "git_object_corrupt", f"ls-tree and the tree objects disagree at {path!r}")
            out.append((mode, kind.decode(), oid.decode(), path))
        if len(out) != len(walked):
            raise Stop(2, "git_object_corrupt", f"ls-tree and the tree objects disagree at {commit}")
        return out


def git_level(r, keys, repo_path):
    repo = Repo(repo_path)
    repo.history_is_original()
    include, with_modes = r["closure_globs"], bool(r.get("closure_modes"))
    done = {}
    for label, key in keys:
        commit, want_full = r["closure_commits"][key], r["closure_ids"][key]
        if commit not in done:
            entries = repo.entries(commit)
            for mode, kind, oid, path in entries:
                if kind == "blob" and is_member(path.decode("utf-8", "surrogateescape"), True, include):
                    repo.check(oid, "blob")
            done[commit] = ids([(m, k, o, p) for m, k, o, p in entries], include, with_modes)
        short, full, n = done[commit]
        if n == 0 or full != want_full or key.split("~")[0] != short:
            raise Stop(1, "closure_mismatch",
                       f"closure {key} of {label!r}: the objects of {commit[:12]} give {short} / {full[:16]}…, "
                       f"the report says {want_full[:16]}…")
    return len(done)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="closure_verify", description=__doc__.split("\n")[0])
    ap.add_argument("report")
    ap.add_argument("--repo")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--version", action="version", version=f"closure_verify {__version__}")
    a = ap.parse_args(argv)
    out = {"verifier": __version__, "report": a.report, "level": None,
           "levels_not_reached": ["structural", "git", "trusted_history"], "closures_verified": 0}
    try:
        try:
            with open(a.report, "rb") as f:
                r = json.loads(f.read().decode("utf-8"))
        except (OSError, ValueError) as e:
            raise Stop(2, "report_unreadable", f"cannot read the report: {e}")
        keys = structural(r)
        out.update(level="structural", levels_not_reached=["git", "trusted_history"])
        if a.repo:
            git_level(r, keys, a.repo)
            out.update(level="git", levels_not_reached=["trusted_history"], closures_verified=len(keys))
        out["result"] = "verified"
        if not keys:
            out["note"] = "the report carries no closure ids: nothing was recomputed"
        rc = 0
    except Stop as s:
        out.update(result="contradicted" if s.exit_code == 1 else "not_verified", reason_code=s.code,
                   message=str(s))
        rc = s.exit_code
    if a.json:
        print(json.dumps(out, indent=2, sort_keys=True))
    else:
        print(f"{out['result']} at level {out['level'] or 'none'}; not claimed: "
              f"{', '.join(out['levels_not_reached'])}; closures recomputed: {out['closures_verified']}")
        if out.get("note"):
            print(out["note"])
    if rc:
        print(out["message"], file=sys.stderr)
        print(f"reason: {out['reason_code']}", file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
