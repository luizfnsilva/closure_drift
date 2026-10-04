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
  closure_drift.py --at commits                 # continuously published output
  closure_drift.py --closure 'src/**/*.py'      # say what determines your output
  closure_drift.py --version-file pyproject.toml --version-regex '...'
  closure_drift.py --json

Exit codes, closed set
  0   clean — every label names exactly one closure at the points compared. Nothing else ends at 0.
  1   drift — a label covers more than one closure AT A PUBLICATION POINT.
  2   no determination, cause named: a refusal on stderr, or a report whose verdict is
      inconclusive, no_labels, empty_closure or no_publication_points.
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

# Onde a versão se esconde quando o pyproject.toml declara `dynamic = ["version"]` — que hoje é a
# NORMA em Python, não a exceção. A v1 respondia "inconclusivo" nesses repositórios, isto é: falhava
# no caso majoritário e chamava a própria falha de resultado.
DYNAMIC_HINTS = [
    (r'^\s*__version__\s*=\s*["\']([^"\']+)["\']', ["src/*/__version__.py", "*/__version__.py",
                                                    "src/*/_version.py", "*/_version.py",
                                                    "src/*/version.py", "*/version.py",
                                                    "src/*/__init__.py", "*/__init__.py"]),
]

CLOSURE_DEFAULTS = ["src/**", "lib/**", "app/**", "*.py", "*.js", "*.ts", "*.rs", "*.go", "*.java"]

# never part of a closure: churn that cannot change behaviour
CLOSURE_EXCLUDE = ["**/test/**", "**/tests/**", "**/*_test.*", "**/*.test.*", "**/spec/**",
                   "**/docs/**", "**/*.md", "**/node_modules/**", "**/vendor/**", "**/.git/**"]


class Refusal(Exception):
    """A named reason why no measurement was produced. Always exit 2, never a traceback."""


# Every git call goes through here. Two things are fixed for all of them:
#   - `core.fsmonitor=false`: a repository's own config can name a command there, and `git status`
#     runs it. Measuring a repository must not execute what that repository says to execute.
#   - `--no-optional-locks`: `git status` otherwise refreshes the index, which is a write to the
#     repository this tool promises never to write to.
GIT = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false"]


def git_bytes(args: list[str], repo: str, may_fail: bool = False) -> bytes | None:
    """Output of a git command. A failure is a Refusal naming the command — unless the caller
    says failure is an answer (may_fail), in which case it is None. It is never empty output:
    0.7.1 read a failed call as "nothing there", and a tag git could not read became a tag that
    was quietly not compared."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", LC_ALL="C")
    try:
        r = subprocess.run([*GIT, "-C", repo, *args], capture_output=True, env=env)
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


def tree(repo: str, sha: str) -> list[tuple[str, str, str]]:
    """[(path, type, object id)] for every file and submodule pointer at a commit.

    `-z`, always. Without it git quotes and octal-escapes any path that is not plain ASCII, the
    quoted form matches no glob, and the file silently leaves the closure: measured on 0.7.1, two
    tags under one label differing only in `src/ação.py` came back `inconclusive`.
    """
    out = git_bytes(["ls-tree", "-r", "-z", sha], repo)
    entries = []
    for record in out.split(b"\0"):
        if not record:
            continue
        meta, _, raw = record.partition(b"\t")
        parts = meta.split()
        if len(parts) < 3:
            continue
        entries.append((raw.decode("utf-8", "surrogateescape"), parts[1].decode(), parts[2].decode()))
    return entries


def closure_hash(entries: list[tuple[str, str, str]], include: list[str]) -> tuple[str, int]:
    """SHA-256 over (path, object id) for every file in the closure.

    v1 ran `git show <sha>:<file>` per file per commit and hashed the bytes: tens of thousands of
    subprocesses, ~0.8s per commit, hours on a real monorepo. It was also redundant — git already
    content-addresses every blob, so the blob OID *is* a hash of the content. One `ls-tree` per
    commit replaces N `show`s and the answer is identical. Using the content-addressing that was
    already there, in a tool about content-addressing, was the obvious move and we missed it.

    A submodule pointer (type `commit`) is part of the closure when its path matches: the commit
    it names decides what code is there. Up to 0.7.1 it was skipped.

    For a repository whose closure holds only ASCII paths and no submodule, the value is
    identical to the one every version since 0.3.0 computed.
    """
    h, n = hashlib.sha256(), 0
    for path, kind, oid in entries:
        if kind not in ("blob", "commit"):
            continue
        if not matches(path, include) or matches(path, CLOSURE_EXCLUDE):
            continue
        h.update(path.encode("utf-8", "surrogateescape"))
        h.update(oid.encode())
        n += 1
    return h.hexdigest()[:16], n


def blob_text(repo: str, oid: str) -> str:
    return git_bytes(["cat-file", "blob", oid], repo).decode("utf-8", errors="replace")


def detect_version_source(repo: str, head: list[tuple[str, str, str]]) -> tuple[str, str] | None:
    blobs = {path: oid for path, kind, oid in head if kind == "blob"}
    for path, pattern in VERSION_SOURCES:
        if path not in blobs:
            continue
        txt = blob_text(repo, blobs[path])
        if re.search(pattern, txt, re.MULTILINE):
            return path, pattern
        # declara versão dinâmica: o rótulo existe, só não está aqui
        if "dynamic" in txt and "version" in txt:
            for pat, globs in DYNAMIC_HINTS:
                for cand in sorted(f for f in blobs if matches(f, globs)):
                    if re.search(pat, blob_text(repo, blobs[cand]), re.MULTILINE):
                        return cand, pat
    return None


def publication_points(repo: str, at: str, limit: int) -> tuple[list[tuple[str, str, str]], int, int]:
    """→ ([(sha, date, name)] em ordem cronológica, total antes do corte, tags que não são commits).
    É a decisão de desenho de toda a v2."""
    if at == "commits":
        total = int(git(["rev-list", "--count", "HEAD"], repo).strip() or 0)
        log = git(["log", f"-{limit}", "--format=%H\t%ad\t%s", "--date=short"], repo)
        return [tuple(l.split("\t", 2)) for l in log.splitlines() if l.count("\t") >= 2][::-1], total, 0
    out = git(["for-each-ref", "--sort=creatordate",
               "--format=%(objectname)\t%(creatordate:short)\t%(refname:short)", "refs/tags"], repo)
    pts, not_commits = [], 0
    for l in out.splitlines():
        if l.count("\t") < 2:
            continue
        sha, date, name = l.split("\t", 2)
        # tag anotada aponta para um objeto tag; resolve para o commit. Uma tag pode apontar para
        # um blob ou uma árvore (chaves públicas, por exemplo): não é ponto de publicação de código,
        # e é contada em vez de derrubar a medição.
        c = git(["rev-parse", "--verify", "--quiet", sha + "^{commit}"], repo, may_fail=True).strip()
        if not c:
            not_commits += 1
            continue
        pts.append((c, date, name))
    return pts[-limit:], len(pts), not_commits


def declared_version(repo: str, entries: list[tuple[str, str, str]], path: str, pattern: str) -> str | None:
    for p, kind, oid in entries:
        if p == path and kind == "blob":
            m = re.search(pattern, blob_text(repo, oid), re.MULTILINE)
            return m.group(1) if m else None
    return None


CONFIG_KEYS = {"at": str, "version_file": str, "version_regex": str, "closure": list}


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
        raise Refusal(f"broken {cfg_path}: {printable(e)}")
    if not isinstance(cfg, dict):
        raise Refusal(f"broken {cfg_path}: it must hold a JSON object, not {type(cfg).__name__}")
    for key, value in cfg.items():
        if key not in CONFIG_KEYS:
            raise Refusal(f"broken {cfg_path}: unknown key {printable(repr(key))}; "
                          f"known keys are {', '.join(sorted(CONFIG_KEYS))}")
        if not isinstance(value, CONFIG_KEYS[key]) or not value:
            raise Refusal(f"broken {cfg_path}: {key!r} must be a non-empty "
                          f"{'list of globs' if key == 'closure' else 'string'}")
    if any(not isinstance(g, str) or not g for g in cfg.get("closure", [])):
        raise Refusal(f"broken {cfg_path}: every entry of 'closure' must be a non-empty string")
    return cfg


def working_tree_state(repo: str) -> tuple[bool | None, str | None]:
    """(dirty, why it was not checked). `git status` runs the clean filter of any modified file
    that `.gitattributes` routes through one, and a filter is a command named in the repository's
    own config. Where the local config defines one, the check is not made and the report says so:
    an unknown is honest, running someone else's command to find out is not."""
    local = git_bytes(["config", "--local", "--list", "-z"], repo, may_fail=True)
    if local is None:
        return None, "the local git config could not be read"
    for item in local.decode("utf-8", "replace").split("\0"):
        key = item.split("\n", 1)[0].lower()
        if re.match(r"^filter\..*\.(clean|smudge|process)$", key) or key.startswith("include"):
            return None, f"not checked: the repository's own git config sets {printable(key)}"
    status = git_bytes(["status", "--porcelain"], repo, may_fail=True)
    if status is None:
        return None, "not checked: this repository has no working tree"
    return bool(status.strip()), None


def run() -> int:
    ap = argparse.ArgumentParser(
        description="Does your version label name exactly one version of your code?")
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--at", choices=["tags", "commits"], default=None,
                    help="where artefacts are published (default: tags, or the repo's config file)")
    ap.add_argument("--closure", action="append", help="glob of files that determine your output")
    ap.add_argument("--version-file")
    ap.add_argument("--version-regex")
    ap.add_argument("--max-commits", type=int, default=400,
                    help="most recent publication points to scan (default 400)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.max_commits < 1:
        raise Refusal(f"--max-commits must be 1 or more, got {a.max_commits}")
    if git_bytes(["rev-parse", "--git-dir"], a.repo, may_fail=True) is None:
        raise Refusal(f"not a git repository: {printable(a.repo)}")
    if git_bytes(["rev-parse", "--verify", "--quiet", "HEAD^{commit}"], a.repo, may_fail=True) is None:
        raise Refusal(f"this repository has no commits: {printable(a.repo)}")

    # A repository may carry its own measurement settings in `.closure-drift.json` at the root:
    #   {"at": "commits", "version_file": "...", "version_regex": "...", "closure": ["glob", ...]}
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

    vfile = a.version_file or cfg.get("version_file")
    vregex = a.version_regex or cfg.get("version_regex")
    if vregex and not vfile:
        raise Refusal("--version-regex needs --version-file (or version_file in "
                      ".closure-drift.json): on its own it would be discarded, unchecked.")
    if vfile:
        vsrc = (vfile, vregex or r'"?version"?\s*[:=]\s*["\']([^"\']+)["\']')
    else:
        vsrc = detect_version_source(a.repo, tree(a.repo, "HEAD"))
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

    pts, total, not_commits = publication_points(a.repo, at, a.max_commits)
    if not pts:
        msg = ("no tags found — this repository publishes nothing addressable by tag. "
               "If it publishes continuously, rerun with --at commits.")
        print(json.dumps({"verdict": "no_publication_points", "note": msg}, indent=1) if a.json else msg,
              file=sys.stderr if not a.json else sys.stdout)
        return 2

    if not a.json:
        print(f"repository        {printable(a.repo)}")
        print(f"version from      {printable(vpath)}")
        print(f"closure           {printable(', '.join(include))}")
        print(f"publication point {at} ({len(pts)} scanned"
              + (f", the most recent of {total}" if total > len(pts) else "") + ")\n")

    by_label: dict[str, dict[str, str]] = defaultdict(dict)   # label -> closure -> first point name
    churn, compared, no_label, empty = 0, 0, 0, 0
    prev_c = None
    for sha, date, name in pts:
        entries = tree(a.repo, sha)
        c, nfiles = closure_hash(entries, include)
        if nfiles == 0:
            empty += 1
            continue
        v = declared_version(a.repo, entries, vpath, vpat)
        if v:
            by_label[v].setdefault(c, f"{name} ({date})")
            compared += 1
        else:
            no_label += 1
        if prev_c is not None and c != prev_c:
            churn += 1
        prev_c = c

    drifting = {v: cs for v, cs in by_label.items() if len(cs) > 1}
    worst = max((len(cs) for cs in by_label.values()), default=0)

    if drifting:
        verdict = "drift"
    elif empty == len(pts):
        verdict = "empty_closure"
    elif not by_label:
        verdict = "no_labels"
    elif len(by_label) == 1:
        verdict = "inconclusive"
    else:
        verdict = "clean"
    # 0 is `clean` and nothing else. Up to 0.7.1 `inconclusive` and `no_labels` also ended at 0,
    # so `closure_drift.py && release` went ahead on a repository about which nothing had been
    # established. An absence of measurement is not a pass.
    code = {"clean": 0, "drift": 1}.get(verdict, 2)

    # O carimbo do próprio laudo. Um relatório que afirma "seu rótulo cobre N estados do seu código"
    # e não diz sob qual HEAD nem com qual versão do detector foi medido é, ele mesmo, um artefato
    # endereçado de forma ambígua — o defeito que este programa existe para encontrar. Sai no JSON
    # porque é o JSON que vira laudo.
    dirty, dirty_note = working_tree_state(a.repo)
    stamp = {
        "measured_at_head": git(["rev-parse", "HEAD"], a.repo).strip()[:12] or "unknown",
        "working_tree_dirty": dirty,
        "detector_closure": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
    }
    if dirty_note:
        stamp["working_tree_dirty_note"] = dirty_note

    if a.json:
        print(json.dumps({
            "stamp": stamp,
            "repo": a.repo, "version_file": vpath, "closure_globs": include,
            "published_at": at, "publication_points": compared + no_label, "labels": len(by_label),
            "labels_covering_multiple_closures": len(drifting),
            "max_closures_per_label": worst, "verdict": verdict,
            "drift": {v: cs for v, cs in drifting.items()},
            "closure_changes_between_points": churn,
            "publication_points_scanned": len(pts),
            "publication_points_compared": compared,
            "points_without_label": no_label,
            "points_with_empty_closure": empty,
            "points_not_commits": not_commits,
            "range_truncated": total > len(pts),
        }, indent=1))
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
            for c, where in cs.items():
                print(f"      closure {c}  first at {printable(where)}")

    print("\n" + "=" * 62)
    if verdict == "drift":
        print(f"DRIFT: {len(drifting)} of {len(by_label)} labels name more than one closure")
        print(f"at a publication point. The worst covers {worst}.")
        print("\nAn artefact addressed by (input, version) is ambiguous for those labels:")
        print("the same address denotes more than one possible output.")
    elif verdict == "empty_closure":
        print("EMPTY CLOSURE: the closure globs match no file at any publication point scanned.")
        print("Nothing was compared. Pass --closure with the files that determine your output.")
    elif verdict == "no_labels":
        print("NO LABELS: no publication point declared a version. Nothing to compare.")
    elif verdict == "inconclusive":
        print("INCONCLUSIVE: only one distinct label across the range scanned.")
    else:
        print(f"CLEAN: each of the {len(by_label)} labels names exactly one closure at publication.")
        print(f"Your version label identifies your code, over the {compared} points compared.")

    # What was NOT compared, said every time. A `clean` over half the tags is a different claim
    # from a `clean` over all of them, and 0.7.1 printed the same line for both.
    print(f"\nPublication points: {len(pts)} scanned, {compared} compared.")
    if no_label:
        print(f"  {no_label} declared no version label there and were not compared.")
    if empty:
        print(f"  {empty} had no file matching the closure globs and were not compared.")
    if not_commits:
        print(f"  {not_commits} tag(s) do not point at a commit and were not scanned.")
    if total > len(pts):
        print(f"  {total - len(pts)} older point(s) are outside --max-commits {a.max_commits} "
              "and were not scanned.")

    print(f"\nBetween publication points the closure changed {churn} time(s). That is development,")
    print("not drift, and is reported only so the two are never confused.")
    print(f"\nMethod: closure = SHA-256 over (path, git object id) for files matching the closure")
    print("globs, evaluated at each publication point. Adjust --closure / --at if these do not")
    print("describe how your output is produced and published.")
    print(f"\nMeasured at HEAD {stamp['measured_at_head']}"
          + (" (working tree DIRTY)" if dirty else "")
          + (f" (working tree {dirty_note})" if dirty_note else "")
          + f", detector closure {stamp['detector_closure']}.")
    print("This report is itself addressed by those two values. A finding without them is a")
    print("finding you cannot return to — which is the defect this tool reports.")
    return code


def main() -> int:
    """The closed set of exit codes is enforced here: nothing leaves this function as a traceback,
    and nothing that is not a measured `drift` leaves it as 1."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    try:
        return run()
    except Refusal as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 — the guard is the point
        print(f"internal error ({type(e).__name__}): no measurement was produced. "
              "This is a defect in closure_drift; please report it.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
