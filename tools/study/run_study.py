#!/usr/bin/env python3
"""Measure the repositories of tools/study/selection.tsv as fixed in tools/study/PREREGISTRATION.md.

    python3 tools/study/run_study.py WORKDIR          # clone, measure, delete; resumable
    python3 tools/study/run_study.py WORKDIR --table  # only rebuild results from what is there
    python3 tools/study/run_study.py WORKDIR --into run3 --shard 2/10 --baseline OLD.py --baseline-into run3-baseline

Defaults only: `closure_drift.py <clone> --json`, nothing else. Writes, next to this file,
results.tsv (one row per repository, none dropped) and results/<owner>__<repo>.json (the
report, as emitted). Standard library and git. Network: the clones.
"""
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DETECTOR = HERE.parent.parent / "closure_drift.py"
TIMEOUT = 15 * 60
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", PYTHONDONTWRITEBYTECODE="1")


def selected():
    for line in (HERE / "selection.tsv").read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        rank, project, repo, status = line.split("\t")
        if status == "selected":
            yield int(rank), project, repo


def remove(path):
    def force(fn, p, _exc):
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        fn(p)
    shutil.rmtree(path, onerror=force)


def option(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def run_detector(detector, clone, repo, row):
    try:
        r = subprocess.run([sys.executable, str(detector), str(clone), "--json"],
                           capture_output=True, env=ENV, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        row["outcome"] = "timeout"
        return row
    row["exit"] = r.returncode
    try:
        report = json.loads(r.stdout.decode("utf-8"))
    except ValueError:
        first = (r.stderr.decode("utf-8", "replace").strip().splitlines() or ["no message"])[0]
        row["outcome"] = "refused"
        row["cause"] = first[:120]
        return row
    report["repo"] = repo                      # the clone's temporary path says nothing
    row["outcome"] = report.get("verdict", "unknown")
    row["report"] = report
    return row


def measure(work: Path, repo: str, baseline=None) -> dict:
    clone = work / (repo.replace("/", "__") + ".git")
    if clone.exists():
        remove(clone)
    row = {"repository": repo}
    try:
        c = subprocess.run(["git", "clone", "--bare", "--quiet",
                            "https://github.com/%s.git" % repo, str(clone)],
                           capture_output=True, env=ENV, timeout=TIMEOUT)
        if c.returncode != 0:
            row["outcome"] = "clone_failed"
            return row
        row["head"] = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"],
                                     capture_output=True, env=ENV).stdout.decode().strip()
        if baseline:
            row["baseline"] = run_detector(baseline, clone, repo, {"repository": repo, "head": row["head"]})
        return run_detector(DETECTOR, clone, repo, row)
    except subprocess.TimeoutExpired:
        row["outcome"] = "clone_failed"
        return row
    finally:
        if clone.exists():
            remove(clone)


def table():
    results = HERE / option("--into", ".") / "results"
    rows = []
    for rank, project, repo in selected():
        f = results / (repo.replace("/", "__") + ".json")
        if not f.exists():
            rows.append((rank, project, repo, "not_measured", "", "", "", "", "", "", ""))
            continue
        row = json.loads(f.read_text(encoding="utf-8"))
        rep = row.get("report") or {}
        rows.append((rank, project, repo, row["outcome"], row.get("exit", ""),
                     rep.get("publication_points_scanned", ""), rep.get("publication_points_compared", ""),
                     rep.get("labels", ""), rep.get("labels_covering_multiple_closures", ""),
                     rep.get("max_closures_per_label", ""), row.get("cause", "")))
    # the detector named is the one stamped in the reports, not the one present when the table is rebuilt
    stamps = sorted({json.loads(f.read_text(encoding="utf-8")).get("report", {}).get("stamp", {}).get("detector_closure", "")
                     for f in results.glob("*.json")} - {""})
    with open(HERE / option("--into", ".") / "results.tsv", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# detector sha256, first 16 hex, as stamped in the reports %s\n" % ",".join(stamps))
        fh.write("# rank\tproject\trepository\toutcome\texit\tscanned\tcompared\tlabels\tlabels_in_drift\tworst\tcause\n")
        for r in rows:
            fh.write("\t".join(str(x) for x in r) + "\n")
    counts = Counter(r[3] for r in rows)
    for outcome, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print("%4d  %s" % (n, outcome))
    determined = counts["clean"] + counts["drift"]
    print("\ndrift: %d of %d where a determination was reached; %d of %d repositories"
          % (counts["drift"], determined, counts["drift"], len(rows)))


def main():
    values = {option(n) for n in ("--into", "--shard", "--baseline", "--baseline-into")}
    args = [a for a in sys.argv[1:] if not a.startswith("--") and a not in values]
    if not args:
        print(__doc__)
        return 2
    work = Path(args[0])
    work.mkdir(parents=True, exist_ok=True)
    results = HERE / option("--into", ".") / "results"
    results.mkdir(parents=True, exist_ok=True)
    shard, of = (int(x) for x in option("--shard", "1/1").split("/"))
    baseline = option("--baseline")
    if "--table" not in sys.argv:
        for i, (rank, project, repo) in enumerate(selected()):
            if i % of != shard - 1:
                continue
            out = results / (repo.replace("/", "__") + ".json")
            if out.exists():
                continue
            row = measure(work, repo, baseline)
            if baseline:
                side = HERE / option("--baseline-into") / "results"
                side.mkdir(parents=True, exist_ok=True)
                (side / out.name).write_text(json.dumps(row.pop("baseline"), indent=1, sort_keys=True) + "\n",
                                             encoding="utf-8")
            out.write_text(json.dumps(row, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            print("%3d %-40s %s" % (rank, repo, row["outcome"]), flush=True)
    table()
    return 0


if __name__ == "__main__":
    sys.exit(main())
