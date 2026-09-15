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

Exit code is 1 only when a label covers more than one closure AT A PUBLICATION POINT.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
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


def git(args: list[str], repo: str) -> str:
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def git_bytes(args: list[str], repo: str) -> bytes | None:
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def matches(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path, g.replace("**/", "*/"))
               or (g.endswith("/**") and path.startswith(g[:-3] + "/")) for g in globs)


def closure_hash(repo: str, sha: str, include: list[str]) -> tuple[str, int]:
    """SHA-256 over (path, blob-oid) for every file in the closure.

    v1 ran `git show <sha>:<file>` per file per commit and hashed the bytes: tens of thousands of
    subprocesses, ~0.8s per commit, hours on a real monorepo. It was also redundant — git already
    content-addresses every blob, so the blob OID *is* a hash of the content. One `ls-tree` per
    commit replaces N `show`s and the answer is identical. Using the content-addressing that was
    already there, in a tool about content-addressing, was the obvious move and we missed it.
    """
    out = git(["ls-tree", "-r", sha], repo)
    h, n = hashlib.sha256(), 0
    for line in out.splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) < 3 or parts[1] != "blob":
            continue
        if not matches(path, include) or matches(path, CLOSURE_EXCLUDE):
            continue
        h.update(path.encode())
        h.update(parts[2].encode())
        n += 1
    return h.hexdigest()[:16], n


def detect_version_source(repo: str) -> tuple[str, str] | None:
    tracked = set(git(["ls-files"], repo).splitlines())
    for path, pattern in VERSION_SOURCES:
        if path not in tracked:
            continue
        blob = git_bytes(["show", f"HEAD:{path}"], repo)
        txt = blob.decode("utf-8", errors="replace") if blob else ""
        if re.search(pattern, txt, re.MULTILINE):
            return path, pattern
        # declara versão dinâmica: o rótulo existe, só não está aqui
        if "dynamic" in txt and "version" in txt:
            for pat, globs in DYNAMIC_HINTS:
                for cand in sorted(f for f in tracked if matches(f, globs)):
                    b = git_bytes(["show", f"HEAD:{cand}"], repo)
                    if b and re.search(pat, b.decode("utf-8", errors="replace"), re.MULTILINE):
                        return cand, pat
    return None


def publication_points(repo: str, at: str, max_commits: int) -> list[tuple[str, str, str]]:
    """→ [(sha, date, name)] em ordem cronológica. É a decisão de desenho de toda a v2."""
    if at == "commits":
        log = git(["log", f"-{max_commits}", "--format=%H\t%ad\t%s", "--date=short"], repo)
        return [tuple(l.split("\t", 2)) for l in log.splitlines() if l.count("\t") >= 2][::-1]
    out = git(["for-each-ref", "--sort=creatordate", "--format=%(objectname)\t%(creatordate:short)\t%(refname:short)",
               "refs/tags"], repo)
    pts = []
    for l in out.splitlines():
        if l.count("\t") < 2:
            continue
        sha, date, name = l.split("\t", 2)
        # tag anotada aponta para um objeto tag; resolve para o commit
        c = git(["rev-list", "-1", sha], repo).strip() or sha
        pts.append((c, date, name))
    return pts[-max_commits:]


def declared_version(repo: str, sha: str, path: str, pattern: str) -> str | None:
    blob = git_bytes(["show", f"{sha}:{path}"], repo)
    if blob is None:
        return None
    m = re.search(pattern, blob.decode("utf-8", errors="replace"), re.MULTILINE)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Does your version label name exactly one version of your code?")
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--at", choices=["tags", "commits"], default=None,
                    help="where artefacts are published (default: tags, or the repo's config file)")
    ap.add_argument("--closure", action="append", help="glob of files that determine your output")
    ap.add_argument("--version-file")
    ap.add_argument("--version-regex")
    ap.add_argument("--max-commits", type=int, default=400)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not git(["rev-parse", "--git-dir"], a.repo):
        print(f"not a git repository: {a.repo}", file=sys.stderr)
        return 2

    # A repository may carry its own measurement settings in `.closure-drift.json` at the root:
    #   {"at": "commits", "version_file": "...", "version_regex": "...", "closure": ["glob", ...]}
    # This exists because the honest configuration for a continuously-publishing system is four
    # long flags, and a measurement that takes four flags does not get run — not in CI, and not
    # when someone says "show me" with thirty seconds and no notes. Committing the configuration
    # next to the code also makes the measurement itself reviewable: the flags become part of the
    # repository's history instead of part of someone's shell history.
    # CLI flags override the file. A broken file is an error, never silently ignored — a tool that
    # measures claims cannot guess what you meant.
    cfg = {}
    cfg_path = Path(a.repo) / ".closure-drift.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(f"broken {cfg_path}: {e}", file=sys.stderr)
            return 2

    at = a.at or cfg.get("at") or "tags"
    if at not in ("tags", "commits"):
        print(f"invalid 'at' in {cfg_path}: {at!r}", file=sys.stderr)
        return 2

    vfile = a.version_file or cfg.get("version_file")
    vregex = a.version_regex or cfg.get("version_regex")
    if vfile:
        vsrc = (vfile, vregex or r'"?version"?\s*[:=]\s*["\']([^"\']+)["\']')
    else:
        vsrc = detect_version_source(a.repo)
        if not vsrc:
            print("could not find a version label. Pass --version-file / --version-regex.", file=sys.stderr)
            print(f"tried: {', '.join(p for p, _ in VERSION_SOURCES)}, and dynamic-version fallbacks.",
                  file=sys.stderr)
            return 2
    vpath, vpat = vsrc
    # 2026-09-15 — a malformed pattern, or one without a capture group, used to raise:
    # `re.error` / `IndexError` left the instrument with exit 1, which is the code for
    # `drift`. An error that cannot be told apart from a finding is worse than no finding.
    # Both are now refusals with the refusal code, named, before any repository is read.
    try:
        _probe = re.compile(vpat)
    except re.error as e:
        print(f"invalid --version-regex {vpat!r}: {e}", file=sys.stderr)
        return 2
    if _probe.groups < 1:
        print(f"--version-regex {vpat!r} has no capture group: "
              "the pattern must capture the version label, e.g. 'version = \"([^\"]+)\"'.",
              file=sys.stderr)
        return 2
    include = a.closure or cfg.get("closure") or CLOSURE_DEFAULTS

    pts = publication_points(a.repo, at, a.max_commits)
    if not pts:
        msg = ("no tags found — this repository publishes nothing addressable by tag. "
               "If it publishes continuously, rerun with --at commits.")
        print(json.dumps({"verdict": "no_publication_points", "note": msg}, indent=1) if a.json else msg,
              file=sys.stderr if not a.json else sys.stdout)
        return 2

    if not a.json:
        print(f"repository        {a.repo}")
        print(f"version from      {vpath}")
        print(f"closure           {', '.join(include)}")
        print(f"publication point {at} ({len(pts)} found)\n")

    by_label: dict[str, dict[str, str]] = defaultdict(dict)   # label -> closure -> first point name
    rows, churn = [], 0
    prev_c = None
    for sha, date, name in pts:
        v = declared_version(a.repo, sha, vpath, vpat)
        c, nfiles = closure_hash(a.repo, sha, include)
        if nfiles == 0:
            continue
        if v:
            by_label[v].setdefault(c, f"{name} ({date})")
        if prev_c is not None and c != prev_c:
            churn += 1
        prev_c = c
        rows.append({"point": name, "date": date, "commit": sha[:10], "label": v,
                     "closure": c, "files": nfiles})

    drifting = {v: cs for v, cs in by_label.items() if len(cs) > 1}
    worst = max((len(cs) for cs in by_label.values()), default=0)

    if not by_label:
        verdict = "no_labels"
    elif drifting:
        verdict = "drift"
    elif len(by_label) == 1:
        verdict = "inconclusive"
    else:
        verdict = "clean"

    # O carimbo do próprio laudo. Um relatório que afirma "seu rótulo cobre N estados do seu código"
    # e não diz sob qual HEAD nem com qual versão do detector foi medido é, ele mesmo, um artefato
    # endereçado de forma ambígua — o defeito que este programa existe para encontrar. Sai no JSON
    # porque é o JSON que vira laudo.
    stamp = {
        "measured_at_head": git(["rev-parse", "HEAD"], a.repo).strip()[:12] or "unknown",
        "working_tree_dirty": bool(git(["status", "--porcelain"], a.repo).strip()),
        "detector_closure": hashlib.sha256(
            __import__("pathlib").Path(__file__).read_bytes()).hexdigest()[:16],
    }

    if a.json:
        print(json.dumps({
            "stamp": stamp,
            "repo": a.repo, "version_file": vpath, "closure_globs": include,
            "published_at": at, "publication_points": len(rows), "labels": len(by_label),
            "labels_covering_multiple_closures": len(drifting),
            "max_closures_per_label": worst, "verdict": verdict,
            "drift": {v: cs for v, cs in drifting.items()},
            "closure_changes_between_points": churn,
        }, indent=1))
        return 1 if verdict == "drift" else 0

    print(f"{'label':28s} {'closures':>9s}")
    print("-" * 44)
    for v, cs in sorted(by_label.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:25]:
        flag = "  <-- names more than one" if len(cs) > 1 else ""
        print(f"{str(v)[:28]:28s} {len(cs):>9d}{flag}")
    if len(by_label) > 25:
        print(f"... and {len(by_label) - 25} more labels")

    if drifting:
        print("\nthe same label at two publications, with different code:")
        for v, cs in list(drifting.items())[:6]:
            print(f"  {v}")
            for c, where in cs.items():
                print(f"      closure {c}  first at {where}")

    print("\n" + "=" * 62)
    if verdict == "drift":
        print(f"DRIFT: {len(drifting)} of {len(by_label)} labels name more than one closure")
        print(f"at a publication point. The worst covers {worst}.")
        print("\nAn artefact addressed by (input, version) is ambiguous for those labels:")
        print("the same address denotes more than one possible output.")
    elif verdict == "no_labels":
        print("NO LABELS: no publication point declared a version. Nothing to compare.")
    elif verdict == "inconclusive":
        print("INCONCLUSIVE: only one distinct label across the range scanned.")
    else:
        print(f"CLEAN: each of the {len(by_label)} labels names exactly one closure at publication.")
        print("Your version label identifies your code, over the range scanned.")

    print(f"\nBetween publication points the closure changed {churn} time(s). That is development,")
    print("not drift, and is reported only so the two are never confused.")
    print(f"\nMethod: closure = SHA-256 over (path, git blob id) for files matching the closure")
    print("globs, evaluated at each publication point. Adjust --closure / --at if these do not")
    print("describe how your output is produced and published.")
    print(f"\nMeasured at HEAD {stamp['measured_at_head']}"
          + (" (working tree DIRTY)" if stamp["working_tree_dirty"] else "")
          + f", detector closure {stamp['detector_closure']}.")
    print("This report is itself addressed by those two values. A finding without them is a")
    print("finding you cannot return to — which is the defect this tool reports.")
    return 1 if verdict == "drift" else 0


if __name__ == "__main__":
    sys.exit(main())
