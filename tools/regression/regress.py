#!/usr/bin/env python3
"""The regression corpus of tests/PREREGISTRATION.md §12.

    python3 tools/regression/regress.py snapshot WORKDIR [--shard K/N]
    python3 tools/regression/regress.py check WORKDIR [--shard K/N] [--detector PATH] [--out FILE]
    python3 tools/regression/regress.py summary FILE...        # merge the outputs of check shards

Snapshot writes tools/regression/corpus/<owner>__<repo>.json. Check compares, field by field, and
prints one line per repository: match, DIFFERS (with the fields), or not checkable (with the cause).
Exit 0 when nothing differs, 1 when something differs, 2 when it could not run. Zero dependencies.
"""
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DETECTOR = ROOT / "closure_drift.py"
CORPUS = HERE / "corpus"
TIMEOUT = 20 * 60
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", PYTHONDONTWRITEBYTECODE="1")
FIELDS = ("verdict", "labels", "labels_covering_multiple_closures", "publication_points_scanned",
          "publication_points_compared", "points_without_label", "points_with_empty_closure",
          "points_label_contradicted")


def selected():
    for line in (ROOT / "tools" / "study" / "selection.tsv").read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            rank, _project, repo, status = line.split("\t")
            if status == "selected":
                yield int(rank), repo


def option(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def remove(path):
    def force(fn, p, _exc):
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        fn(p)
    if path.exists():
        shutil.rmtree(path, onerror=force)


def git(clone, *args, check=True):
    r = subprocess.run(["git", "-C", str(clone), *args], capture_output=True, env=ENV)
    if check and r.returncode:
        raise RuntimeError("git %s: %s" % (args[0], r.stderr.decode("utf-8", "replace").strip()[:200]))
    return r.stdout.decode("utf-8", "replace")


def tags(clone):
    out = {}
    for line in git(clone, "for-each-ref", "--format=%(refname) %(objectname)", "refs/tags").splitlines():
        ref, oid = line.rsplit(" ", 1)
        out[ref[len("refs/tags/"):]] = oid
    return out


def measure(detector, clone):
    """→ (exit, report or None, first line of stderr)"""
    r = subprocess.run([sys.executable, str(detector), str(clone), "--json"], capture_output=True,
                       env=ENV, timeout=TIMEOUT)
    try:
        report = json.loads(r.stdout.decode("utf-8"))
    except ValueError:
        report = None
    err = (r.stderr.decode("utf-8", "replace").strip().splitlines() or [""])[0][:200]
    return r.returncode, report, err


def essence(code, report, err):
    """What is compared: the fields of §12, the exit code, and the closure ids under each label in drift."""
    if report is None:
        return {"exit": code, "refusal": err}
    out = {"exit": code}
    for f in FIELDS:
        if f in report:
            out[f] = report[f]
    ids = report.get("closure_ids", {})
    out["drift"] = {label: sorted(ids.get(k, k) for k in keys)
                    for label, keys in sorted((report.get("drift") or {}).items())}
    return out


def clone_into(work, repo):
    clone = work / (repo.replace("/", "__") + ".git")
    remove(clone)
    r = subprocess.run(["git", "clone", "--bare", "--quiet", "https://github.com/%s.git" % repo, str(clone)],
                       capture_output=True, env=ENV, timeout=TIMEOUT)
    if r.returncode:
        raise RuntimeError("clone failed: " + r.stderr.decode("utf-8", "replace").strip()[:200])
    return clone


def snapshot(work, shard, of):
    CORPUS.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(DETECTOR.read_bytes()).hexdigest()
    for i, (rank, repo) in enumerate(selected()):
        if i % of != shard - 1:
            continue
        target = CORPUS / (repo.replace("/", "__") + ".json")
        row = {"repository": repo, "rank": rank, "detector_sha256": sha}
        try:
            clone = clone_into(work, repo)
            row["head"] = git(clone, "rev-parse", "HEAD").strip()
            row["tags"] = tags(clone)
            row["expected"] = essence(*measure(DETECTOR, clone))
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            row["not_recorded"] = str(e)[:200]
        finally:
            remove(work / (repo.replace("/", "__") + ".git"))
        target.write_text(json.dumps(row, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("%3d %-40s %s" % (rank, repo, row.get("expected", {}).get("verdict") or row.get("not_recorded")),
              flush=True)


def pin(clone, row):
    """Make the clone hold exactly the recorded state; → None, or why it cannot."""
    have = subprocess.run(["git", "-C", str(clone), "cat-file", "-e", row["head"] + "^{commit}"],
                          capture_output=True, env=ENV).returncode == 0
    if not have:
        return "the recorded HEAD %s is no longer in the repository" % row["head"][:12]
    now = tags(clone)
    moved = sorted(t for t, oid in row["tags"].items() if now.get(t) != oid)
    if moved:
        return "%d recorded tag(s) missing or moved upstream, e.g. %s" % (len(moved), moved[0])
    for extra in sorted(set(now) - set(row["tags"])):
        git(clone, "update-ref", "-d", "refs/tags/" + extra)
    git(clone, "update-ref", "--no-deref", "HEAD", row["head"])
    return None


def check(work, shard, of, detector, out_file):
    results = []
    for i, (rank, repo) in enumerate(selected()):
        if i % of != shard - 1:
            continue
        row = json.loads((CORPUS / (repo.replace("/", "__") + ".json")).read_text(encoding="utf-8"))
        res = {"repository": repo, "rank": rank}
        if "expected" not in row:
            res.update(state="not checkable", cause="no snapshot: " + row.get("not_recorded", "?"))
        else:
            try:
                clone = clone_into(work, repo)
                why = pin(clone, row)
                if why:
                    res.update(state="not checkable", cause=why)
                else:
                    got = essence(*measure(detector, clone))
                    want = row["expected"]
                    # a field the older report does not carry is not compared
                    keys = sorted(set(want) & set(got))
                    diff = {k: [want[k], got[k]] for k in keys if want[k] != got[k]}
                    res.update(state="DIFFERS" if diff else "match", differs=diff)
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                res.update(state="not checkable", cause=str(e)[:200])
            finally:
                remove(work / (repo.replace("/", "__") + ".git"))
        results.append(res)
        print("%3d %-40s %s %s" % (rank, repo, res["state"], res.get("cause") or
                                   ", ".join(sorted(res.get("differs", {})))), flush=True)
    if out_file:
        Path(out_file).write_text(json.dumps({"detector_sha256": hashlib.sha256(Path(detector).read_bytes()).hexdigest(),
                                              "results": results}, indent=1) + "\n", encoding="utf-8")
    return 1 if any(r["state"] == "DIFFERS" for r in results) else 0


def summary(files):
    rows, shas = [], set()
    for f in files:
        doc = json.loads(Path(f).read_text(encoding="utf-8"))
        shas.add(doc["detector_sha256"])
        rows += doc["results"]
    rows.sort(key=lambda r: r["rank"])
    n = {s: sum(1 for r in rows if r["state"] == s) for s in ("match", "DIFFERS", "not checkable")}
    print("detector %s" % ", ".join(sorted(shas)))
    for r in rows:
        if r["state"] != "match":
            print("%3d %-40s %s %s" % (r["rank"], r["repository"], r["state"],
                                       r.get("cause") or json.dumps(r.get("differs"), ensure_ascii=True)[:300]))
    print("\n%d repositories · %d match · %d differ · %d not checkable"
          % (len(rows), n["match"], n["DIFFERS"], n["not checkable"]))
    return 1 if n["DIFFERS"] else 0


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("snapshot", "check", "summary"):
        print(__doc__)
        return 2
    if sys.argv[1] == "summary":
        return summary(sys.argv[2:])
    work = Path(sys.argv[2])
    work.mkdir(parents=True, exist_ok=True)
    shard, of = (int(x) for x in option("--shard", "1/1").split("/"))
    if sys.argv[1] == "snapshot":
        snapshot(work, shard, of)
        return 0
    return check(work, shard, of, Path(option("--detector", str(DETECTOR))), option("--out"))


if __name__ == "__main__":
    sys.exit(main())
