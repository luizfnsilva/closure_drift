#!/usr/bin/env python3
"""Measure one large repository as tools/benchmark/PREREGISTRATION.md says.

    python3 tools/benchmark/run_benchmark.py torvalds/linux --out tools/benchmark/results

Clones it bare into --work, runs B1..B7 under the time limit, writes one JSON file and the
reports, deletes the clone. POSIX only (it reads peak memory from wait4). Zero dependencies.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DETECTOR = ROOT / "closure_drift.py"
ORACLE = ROOT / "tests" / "oracle.py"
LIMIT = 40 * 60
KEEP = 4 << 20          # a report larger than this is recorded by hash and size only


def tree_rss_kb(root_pid):
    """Resident memory of a process and all its descendants, now, in kB (Linux /proc)."""
    children, rss = {}, {}
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open("/proc/%s/status" % d) as f:
                fields = dict(line.split(":", 1) for line in f if ":" in line)
            children.setdefault(int(fields["PPid"]), []).append(int(d))
            rss[int(d)] = int(fields.get("VmRSS", "0 kB").split()[0])
        except (OSError, ValueError, KeyError):
            continue
    total, todo = 0, [root_pid]
    while todo:
        pid = todo.pop()
        total += rss.get(pid, 0)
        todo += children.get(pid, [])
    return total


def timed(cmd, out_path, limit=LIMIT):
    """Run cmd with stdout to a file. → dict(exit, seconds, peak_mb (largest single process),
    tree_peak_mb (the process and its children together, sampled), stderr_first, timed_out)."""
    err_path = str(out_path) + ".stderr"
    with open(out_path, "wb") as out, open(err_path, "wb") as err:
        start = time.monotonic()
        p = subprocess.Popen(cmd, stdout=out, stderr=err, stdin=subprocess.DEVNULL)
        timed_out, status, usage, tree_peak, sampled = False, None, None, 0, os.path.isdir("/proc")
        while True:
            if sampled:
                tree_peak = max(tree_peak, tree_rss_kb(p.pid))
            pid, status, usage = os.wait4(p.pid, os.WNOHANG)
            if pid:
                break
            if time.monotonic() - start > limit:
                timed_out = True
                p.kill()
                _pid, status, usage = os.wait4(p.pid, 0)
                break
            time.sleep(0.05)
        seconds = time.monotonic() - start
    p.returncode = 0          # reaped above; stop Popen from waiting again
    if os.WIFSIGNALED(status):
        code = -os.WTERMSIG(status)
    else:
        code = os.WEXITSTATUS(status)
    peak = usage.ru_maxrss / (1 << 20 if sys.platform == "darwin" else 1 << 10)
    stderr = Path(err_path).read_bytes().decode("utf-8", "replace")
    os.unlink(err_path)
    return {"exit": code, "seconds": round(seconds, 2), "peak_mb": round(peak, 1),
            "tree_peak_mb": round(tree_peak / 1024, 1) if sampled else None,
            "stderr_first": (stderr.strip().splitlines() or [""])[0][:300],
            "stderr_has_traceback": "Traceback" in stderr or "internal error" in stderr,
            "timed_out": timed_out}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True).stdout


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def summary(path):
    """The fields of a report this table prints; {} when stdout is not a report."""
    try:
        r = json.loads(Path(path).read_bytes().decode("utf-8"))
    except (ValueError, OSError):
        return {}
    keep = ("verdict", "labels", "labels_covering_multiple_closures", "max_closures_per_label",
            "publication_points_scanned", "publication_points_compared", "points_without_label",
            "points_with_empty_closure", "points_label_contradicted", "range_truncated", "version_file",
            "label_at_head")
    out = {k: r[k] for k in keep if k in r}
    if "stamp" in r:
        out["detector_closure"] = r["stamp"].get("detector_closure")
    if "diagnostics" in r:
        out["objects_read"] = r["diagnostics"].get("objects_read")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="owner/name on GitHub")
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default=os.environ.get("RUNNER_TEMP", "/tmp"))
    ap.add_argument("--baseline", help="an earlier closure_drift.py: B3 is run with it too, on the same clone")
    a = ap.parse_args()

    name = a.slug.replace("/", "__")
    out = Path(a.out) / name
    out.mkdir(parents=True, exist_ok=True)
    clone = Path(a.work) / (name + ".git")
    if clone.exists():
        shutil.rmtree(clone)

    result = {
        "repository": a.slug,
        "detector_sha256": sha(DETECTOR),
        "baseline_sha256": sha(a.baseline) if a.baseline else None,
        "oracle_sha256": sha(ORACLE),
        "machine": {"platform": platform.platform(), "cpus": os.cpu_count(),
                    "python": sys.version.split()[0],
                    "git": subprocess.run(["git", "--version"], capture_output=True).stdout.decode().strip(),
                    "runner": os.environ.get("ImageOS", "") + " " + os.environ.get("ImageVersion", "")},
        "limit_seconds": LIMIT, "runs": {}, "failures": [],
    }
    try:
        with open("/proc/meminfo") as f:
            result["machine"]["memory_mb"] = int(f.readline().split()[1]) // 1024
    except OSError:
        pass

    start = time.monotonic()
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    c = subprocess.run(["git", "clone", "--bare", "--quiet", f"https://github.com/{a.slug}.git", str(clone)],
                       capture_output=True, env=env)
    result["clone"] = {"exit": c.returncode, "seconds": round(time.monotonic() - start, 1)}
    if c.returncode != 0:
        result["clone"]["stderr_first"] = (c.stderr.decode("utf-8", "replace").strip().splitlines() or [""])[0][:300]
        result["failures"].append("clone_failed")
        (Path(a.out) / (name + ".json")).write_text(json.dumps(result, indent=1) + "\n")
        return 0

    refs = git(clone, "for-each-ref", "--sort=creatordate",
               "--format=%(objecttype) %(*objecttype) %(refname)", "refs/tags").decode("utf-8", "replace")
    tags = [l.split(" ", 2)[2][len("refs/tags/"):] for l in refs.splitlines()
            if "commit" in l.split(" ", 2)[:2]]
    result["clone"].update({
        "disk_mb": round(sum(f.stat().st_size for f in clone.rglob("*") if f.is_file()) / (1 << 20)),
        "tags": len(refs.splitlines()), "tags_at_commits": len(tags),
        "commits_from_head": int(git(clone, "rev-list", "--count", "HEAD")),
        "files_at_head": git(clone, "ls-tree", "-r", "-z", "--name-only", "HEAD").count(b"\0"),
        "head": git(clone, "rev-parse", "HEAD").decode().strip(),
    })

    det = [sys.executable, str(DETECTOR), str(clone)]
    recipes = json.loads((Path(__file__).parent / "recipes.json").read_text(encoding="utf-8"))
    plan = [("B1", det + ["--json"]), ("B2", det + ["--json"]),
            ("B3", det + ["--json", "--max-commits", "1000000", "--diagnose"]),
            ("B4", det + ["--would-tag", "--json"]),
            ("B5", det + ["--at", "commits", "--json"])]
    if a.baseline:
        plan.append(("B3_baseline", [sys.executable, a.baseline, str(clone), "--json", "--max-commits", "1000000"]))
    if a.slug in recipes:
        plan.append(("B8", det + ["--json", "--max-commits", "1000000", "--diagnose"] + recipes[a.slug]))
    pairs = []
    if len(tags) >= 2:
        oldest, median, newest = tags[0], tags[len(tags) // 2], tags[-1]
        pairs = [("oldest_newest", oldest, newest), ("median_newest", median, newest)]
        result["tags_picked"] = {"oldest": oldest, "median": median, "newest": newest}
        for label, x, y in pairs:
            plan.append((f"B6_{label}", det + ["--compare", x, y, "--json"]))
            plan.append((f"B7_{label}", [sys.executable, str(ORACLE), str(clone), "--compare", x, y]))

    for run_id, cmd in plan:
        path = out / (run_id + ".json")
        r = timed(cmd, path)
        r["stdout_sha256"], r["stdout_bytes"] = sha(path), path.stat().st_size
        r["command"] = " ".join(cmd[1:]).replace(str(clone), "CLONE").replace(str(ROOT) + "/", "")
        if run_id[:2] != "B7":
            r.update(summary(path))
        result["runs"][run_id] = r
        print(f"{run_id:18s} exit {r['exit']:>3}  {r['seconds']:>8.1f} s  {r['peak_mb']:>8.0f} MB  "
              f"{r.get('verdict', '')}  {r['stderr_first'][:80]}", flush=True)
        if r["timed_out"]:
            result["failures"].append(f"F1 {run_id}")
        elif r["exit"] not in (0, 1, 2) and run_id[:2] != "B7":
            result["failures"].append(f"F2 {run_id} exit {r['exit']}")
        if r["stderr_has_traceback"]:
            result["failures"].append(f"F3 {run_id}")

    runs = result["runs"]
    if not runs["B1"]["timed_out"] and not runs["B2"]["timed_out"] \
            and runs["B1"]["stdout_sha256"] != runs["B2"]["stdout_sha256"]:
        result["failures"].append("F4 B1 and B2 differ")
    for label, _x, _y in pairs:
        d_run, o_run = runs[f"B6_{label}"], runs[f"B7_{label}"]
        check = {"compared": False}
        try:
            d = json.loads((out / f"B6_{label}.json").read_bytes().decode("utf-8"))
            o = json.loads((out / f"B7_{label}.json").read_bytes().decode("utf-8"))
        except ValueError:
            check["reason"] = "one side printed no report"
        else:
            if "a" not in d:
                check["reason"] = "the detector printed no comparison: " + str(d.get("verdict") or d_run["stderr_first"])
            else:
                check["compared"] = True
                ids = all(d[s]["closure_id"] == o[s]["closure_id"] and d[s]["files"] == o[s]["files"] for s in "ab")
                lists = all(d[k] == o[k] for k in ("changed", "only_in_a", "only_in_b"))
                check.update({"ids_and_counts_agree": ids, "path_lists_agree": lists,
                              "files": [d["a"]["files"], d["b"]["files"]],
                              "paths_differing": len(d["changed"]) + len(d["only_in_a"]) + len(d["only_in_b"])})
                if not ids:
                    result["failures"].append(f"F5 {label}")
                if not lists:
                    result["failures"].append(f"F6 {label}")
        result.setdefault("oracle", {})[label] = check
        if o_run["exit"] != 0:
            check["oracle_exit"] = o_run["exit"]

    for f in out.iterdir():          # large reports are recorded by hash and size, not kept
        if f.stat().st_size > KEEP:
            f.unlink()
    shutil.rmtree(clone, ignore_errors=True)
    (Path(a.out) / (name + ".json")).write_text(json.dumps(result, indent=1) + "\n")
    print("failures:", result["failures"] or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
