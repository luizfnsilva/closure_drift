#!/usr/bin/env python3
"""MCP server (stdio) for closure_drift. Standard library only.

It lets an AI agent ask, before it tags or publishes, whether a version label
names exactly one code state. It runs closure_drift.py read-only and returns
its JSON report with the exit code: 0 clean, 1 drift, 2 anything else.

The script is found in CLOSURE_DRIFT_SCRIPT, or two folders up from here.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.environ.get("CLOSURE_DRIFT_SCRIPT") or os.path.join(HERE, "..", "..", "closure_drift.py")
TIMEOUT = 900
MEANING = {0: "clean: each label names one code state",
           1: "drift: a label names more than one code state",
           2: "not decided: read 'output' for the reason"}

REPO = {"type": "string", "description": "path to a local git repository"}
TOOLS = [
    {"name": "check_versions",
     "description": "Does each version label in this git repository name exactly one code state across its tags? Read-only.",
     "inputSchema": {"type": "object", "required": ["repo"], "properties": {
         "repo": REPO,
         "published_file": {"type": "string", "description": "optional file with the versions actually released, one per line"},
         "strict": {"type": "boolean", "description": "clean only if every tag scanned was compared"}}}},
    {"name": "would_tag",
     "description": "Run BEFORE creating a release tag: would HEAD reuse a version label that already names other code? Read-only.",
     "inputSchema": {"type": "object", "required": ["repo"], "properties": {"repo": REPO}}},
    {"name": "explain_label",
     "description": "List the paths that differ under one version label found in drift. Read-only.",
     "inputSchema": {"type": "object", "required": ["repo", "label"], "properties": {
         "repo": REPO, "label": {"type": "string"}}}},
    {"name": "compare",
     "description": "Compare two tags or commits: their version labels, closures and the paths that differ. Read-only.",
     "inputSchema": {"type": "object", "required": ["repo", "a", "b"], "properties": {
         "repo": REPO, "a": {"type": "string"}, "b": {"type": "string"}}}},
]


def run(args: list) -> dict:
    try:
        p = subprocess.run([sys.executable, SCRIPT] + args, capture_output=True, text=True,
                           timeout=TIMEOUT, errors="replace")
    except subprocess.TimeoutExpired:
        return {"exit": 2, "meaning": MEANING[2], "output": f"timed out after {TIMEOUT} s"}
    out = p.stdout.strip() or p.stderr.strip()
    try:
        out = json.loads(out)
    except ValueError:
        pass
    code = p.returncode if p.returncode in MEANING else 2
    return {"exit": code, "meaning": MEANING[code], "output": out}


def call(name: str, a: dict) -> dict:
    repo = a["repo"]
    if name == "check_versions":
        args = ["--json"]
        if a.get("published_file"):
            args += ["--published", a["published_file"]]
        if a.get("strict"):
            args.append("--strict")
        return run(args + [repo])
    if name == "would_tag":
        return run(["--would-tag", "--json", repo])
    if name == "explain_label":
        return run(["--explain", a["label"], "--json", repo])
    if name == "compare":
        return run(["--compare", a["a"], a["b"], "--json", repo])
    raise KeyError(name)


def reply(i, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": i}
    msg.update({"error": error} if error else {"result": result})
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        try:
            req = json.loads(line)
        except ValueError:
            continue
        i, method = req.get("id"), req.get("method")
        if i is None:
            continue                                    # notification
        p = req.get("params") or {}
        if method == "initialize":
            reply(i, {"protocolVersion": p.get("protocolVersion", "2025-06-18"),
                      "capabilities": {"tools": {}},
                      "serverInfo": {"name": "closure_drift", "version": "1.1.0"}})
        elif method == "tools/list":
            reply(i, {"tools": TOOLS})
        elif method == "tools/call":
            try:
                res = call(p["name"], p.get("arguments") or {})
                reply(i, {"content": [{"type": "text", "text": json.dumps(res, indent=1)}],
                          "isError": False})
            except (KeyError, TypeError) as e:
                reply(i, {"content": [{"type": "text", "text": f"bad call: {e}"}], "isError": True})
        elif method == "ping":
            reply(i, {})
        else:
            reply(i, error={"code": -32601, "message": f"unknown method {method}"})


if __name__ == "__main__":
    main()
