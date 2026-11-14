"""§35 differential hook. Loaded at interpreter start by a .pth line ("import cd_diffhook") in a
dedicated venv. When the script being run is the candidate closure_drift.py, runs the reference and
the candidate with the same argv, env, cwd and stdin, writes one JSON line per call to CD_DIFF_LOG, and
replays the candidate's result. Standard library only."""
import hashlib, json, os, re, subprocess, sys

def _log(rec):
    with open(os.environ["CD_DIFF_LOG"], "a") as fh:
        fh.write(json.dumps(rec) + "\n")

def _main():
    if not os.environ.get("CD_DIFF_LOG"):
        return
    argv = getattr(sys, "orig_argv", None) or []
    named = any(os.path.basename(x) == "closure_drift.py" for x in argv[1:])
    if os.environ.get("CD_DIFF_INNER"):
        if named:
            _log({"kind": "seen", "how": "inner"})
        return
    if not named:
        return
    if "-c" in argv[1:]:
        _log({"kind": "seen", "how": "module_call"})
        return
    script = next((a for a in argv[1:] if not a.startswith("-")), None)
    if script is None or os.path.basename(script) != "closure_drift.py":
        _log({"kind": "seen", "how": "other", "argv": argv[1:4]})
        return
    _log({"kind": "seen", "how": "compared"})
    import uuid
    cid = uuid.uuid4().hex[:12]
    _log({"kind": "start", "id": cid})
    cand = os.path.abspath(script)
    ref = os.environ["CD_DIFF_REF"]
    i = argv.index(script)
    args = argv[i + 1:]
    stdin = b"" if sys.stdin is None or sys.stdin.isatty() else sys.stdin.buffer.read()
    env = dict(os.environ, CD_DIFF_INNER="1")
    def run(path):
        return subprocess.run([sys.executable, *argv[1:i], path, *args], input=stdin,
                              capture_output=True, env=env, cwd=os.getcwd())
    r_ref, r_cand = run(ref), run(cand)
    refdir, canddir = os.path.dirname(ref), os.path.dirname(cand)
    def norm(b, is_ref):
        s = b.decode("utf-8", "surrogateescape")
        if is_ref:
            s = s.replace(refdir, canddir)
        s = re.sub(r'"version":\s*"[^"]*"', '"version": "N"', s)
        s = re.sub(r"\b[0-9a-f]{16}\b", "<sha16>", s)
        s = re.sub(r"\b[0-9a-f]{64}\b", "<sha64>", s)
        return s
    same = (r_ref.returncode == r_cand.returncode and norm(r_ref.stdout, 1) == norm(r_cand.stdout, 0)
            and norm(r_ref.stderr, 1) == norm(r_cand.stderr, 0))
    rec = {"kind": "call", "id": cid, "same": same, "args": args, "cwd": os.getcwd(),
           "stdin_sha": hashlib.sha256(stdin).hexdigest()[:16],
           "exit": [r_ref.returncode, r_cand.returncode]}
    if not same:
        rec.update(ref_out=norm(r_ref.stdout, 1)[-1500:], cand_out=norm(r_cand.stdout, 0)[-1500:],
                   ref_err=norm(r_ref.stderr, 1)[-800:], cand_err=norm(r_cand.stderr, 0)[-800:])
    _log(rec)
    _log({"kind": "end", "id": cid})
    sys.stdout.buffer.write(r_cand.stdout); sys.stdout.flush()
    sys.stderr.buffer.write(r_cand.stderr); sys.stderr.flush()
    os._exit(r_cand.returncode)

try:
    _main()
except SystemExit:
    raise
except BaseException as e:   # a harness failure is a failure, never an equivalence (§35 am. 3)
    try:
        _log({"kind": "harness_error", "error": repr(e)[:300]})
    finally:
        os._exit(97)
