#!/usr/bin/env python3
"""§35 am. 1: operational cost, reference against candidate. The repositories are the first five of
tools/regression/corpus/ in alphabetical order (fixed by this rule, not chosen by result), cloned in full and
checked out at their pinned `head`. Each detector runs REPS times per repository, alternating; a `git` wrapper
first on PATH counts subprocesses. Prints, per repository, median wall seconds and git calls per run.
    python3 cost.py REF.py CAND.py WORKDIR [REPS]"""
import json, os, statistics, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
ref, cand, work = sys.argv[1], sys.argv[2], Path(sys.argv[3]); reps = int(sys.argv[4]) if len(sys.argv) > 4 else 5
work.mkdir(parents=True, exist_ok=True)
real_git = subprocess.run(["sh", "-c", "command -v git"], capture_output=True, text=True).stdout.strip()
shim = work / "shim"; shim.mkdir(exist_ok=True)
(shim / "git").write_text(f'#!/bin/sh\necho x >> "$CD_GIT_COUNT"\nexec "{real_git}" "$@"\n'); (shim / "git").chmod(0o755)
corpus = sorted((ROOT / "tools/regression/corpus").glob("*.json"))[:5]
rows = []
for f in corpus:
    pin = json.loads(f.read_text()); repo = pin["repository"]; d = work / f.stem
    if not d.exists():
        subprocess.run([real_git, "clone", "-q", f"https://github.com/{repo}", str(d)], check=True)
    subprocess.run([real_git, "-C", str(d), "checkout", "-q", "--detach", pin["head"]], check=True)
    res = {}
    for k in range(reps):
        for name, det in (("ref", ref), ("cand", cand)) if k % 2 == 0 else (("cand", cand), ("ref", ref)):
            cnt = work / f"count-{name}"; cnt.write_text("")
            env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}", CD_GIT_COUNT=str(cnt))
            t = time.perf_counter()
            r = subprocess.run([sys.executable, det, str(d), "--json"], capture_output=True, env=env)
            dt = time.perf_counter() - t
            res.setdefault(name, []).append((dt, len(cnt.read_text().splitlines()), r.returncode))
    line = {"repo": repo}
    for name in ("ref", "cand"):
        xs = res[name]
        line[name] = {"median_s": round(statistics.median(x[0] for x in xs), 3),
                      "git_calls": sorted({x[1] for x in xs}), "exit": sorted({x[2] for x in xs})}
    rows.append(line); print(json.dumps(line), flush=True)
