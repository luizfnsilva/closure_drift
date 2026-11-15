#!/usr/bin/env python3
"""§37 P37-2: seven edits (and an eighth, amendment 1) — of the report or of the Git objects — and the code each must end in.
Each case runs on its own copy, after an unedited control that must verify. Standard library only.

    python3 tests/verify_adversarial.py          # exit 0 when every case gives its expected code
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETECTOR = os.path.join(ROOT, "closure_drift.py")
VERIFIER = os.environ.get("CLOSURE_VERIFY", os.path.join(ROOT, "closure_verify.py"))
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@t", GIT_AUTHOR_DATE="2026-01-01T00:00:00Z",
           GIT_COMMITTER_DATE="2026-01-01T00:00:00Z", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, env=ENV).stdout.decode()


def fixture(where):
    repo = os.path.join(where, "r")
    os.makedirs(os.path.join(repo, "src"))
    git(repo, "init", "-q")
    with open(os.path.join(repo, "pyproject.toml"), "w") as f:
        f.write('[project]\nname = "x"\nversion = "1.0"\n')
    for n, body in enumerate(["a\n", "b\n", "c\n"]):
        with open(os.path.join(repo, "src", "a.py"), "w") as f:
            f.write(body)
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", str(n + 1))
    out = subprocess.run([sys.executable, DETECTOR, repo, "--at", "commits", "--json"], capture_output=True)
    report = json.loads(out.stdout)
    assert report["verdict"] == "drift", report["verdict"]
    return repo, report


def verify(report, repo):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(report, f)
    p = subprocess.run([sys.executable, VERIFIER, f.name, "--repo", repo, "--json"], capture_output=True)
    os.unlink(f.name)
    return p.returncode, json.loads(p.stdout).get("reason_code")


def overwrite_loose(repo, oid, body):
    path = os.path.join(repo, ".git", "objects", oid[:2], oid[2:])
    os.chmod(path, 0o644)
    with open(path, "wb") as f:
        f.write(zlib.compress(b"blob %d\0" % len(body) + body))


def first(report):
    return sorted(report["closure_ids"])[0]


def case_full_id(repo, r):
    k = first(r)
    r["closure_ids"][k] = ("0" if r["closure_ids"][k][0] != "0" else "1") + r["closure_ids"][k][1:]


def case_commit(repo, r):
    keys = sorted(r["closure_commits"])
    r["closure_commits"][keys[0]] = r["closure_commits"][keys[1]]


def case_remove_id(repo, r):
    del r["closure_ids"][first(r)]


def case_count(repo, r):
    r["labels_covering_multiple_closures"] += 1


def case_blob(repo, r):
    commit = r["closure_commits"][first(r)]
    oid = git(repo, "rev-parse", commit + ":src/a.py").strip()
    overwrite_loose(repo, oid, b"tampered\n")


def case_replace(repo, r):
    commit = r["closure_commits"][first(r)]
    other = [c for c in r["closure_commits"].values() if c != commit][0]
    git(repo, "replace", commit, other)


def case_missing(repo, r):
    commit = r["closure_commits"][first(r)]
    r["closure_commits"][first(r)] = commit[::-1]          # a well-formed id this repository does not hold


def case_key(repo, r):
    k = first(r)
    new = ("0" if k[0] != "0" else "1") + k[1:]
    for label in r["drift"].values():
        if k in label:
            label[new] = label.pop(k)
    r["closure_ids"][new] = r["closure_ids"].pop(k)
    r["closure_commits"][new] = r["closure_commits"].pop(k)


CASES = [("full id changed", case_full_id, 1, "closure_mismatch"),
         ("commit changed to another real one", case_commit, 1, "closure_mismatch"),
         ("closure removed from closure_ids", case_remove_id, 1, "report_inconsistent"),
         ("count changed", case_count, 1, "report_inconsistent"),
         ("loose blob overwritten", case_blob, 2, "git_object_corrupt"),
         ("git replace on the commit", case_replace, 2, "git_history_rewritten"),
         ("commit not in this repository", case_missing, 2, "object_missing"),
         ("short key renamed everywhere (am. 1)", case_key, 1, "closure_mismatch")]


def main():
    work = tempfile.mkdtemp(prefix="cd-verify-")
    try:
        base, report = fixture(work)
        failed = 0
        control = verify(report, base)
        print(f"{'control (unedited)':40s} {control}")
        failed += control != (0, None)
        for name, edit, rc, code in CASES:
            repo = os.path.join(work, name.replace(" ", "_"))
            shutil.copytree(base, repo, symlinks=True)
            r = json.loads(json.dumps(report))
            if verify(r, repo) != (0, None):
                print(f"{name:40s} its own control did not verify"); failed += 1; continue
            edit(repo, r)
            got = verify(r, repo)
            ok = got == (rc, code)
            failed += not ok
            print(f"{name:40s} {got} {'ok' if ok else f'EXPECTED {(rc, code)}'}")
        print(f"\n{len(CASES)} of {len(CASES)} cases as pre-registered" if not failed else f"\n{failed} FAILED")
        return 1 if failed else 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
