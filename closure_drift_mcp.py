#!/usr/bin/env python3
"""MCP server (stdio) for closure_drift. Standard library only.

It lets an AI agent ask, before it tags or publishes, whether a version label
names exactly one code state. It runs closure_drift.py read-only and returns
its JSON report with the exit code: 0 clean, 1 drift, 2 anything else.

    uvx --from git+https://github.com/luizfnsilva/closure_drift closure-drift-mcp

The detector is CLOSURE_DRIFT_SCRIPT when set, else the closure_drift.py
installed or kept next to this file.
"""
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def detector() -> str:
    given = os.environ.get("CLOSURE_DRIFT_SCRIPT")
    if given:
        return given
    beside = os.path.join(HERE, "closure_drift.py")
    if os.path.isfile(beside):
        return beside
    spec = importlib.util.find_spec("closure_drift")
    return spec.origin if spec and spec.origin else beside


SCRIPT = detector()
TIMEOUT = 900
MEANING = {0: "clean: each label names one code state",
           1: "drift: a label names more than one code state",
           2: "not decided: read 'output' for the reason"}

REPO = {"type": "string", "description": "path to a local git repository with its tags fetched"}
ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
OUTPUT = {"type": "object", "required": ["exit", "meaning", "output"], "properties": {
    "exit": {"type": "integer", "enum": [0, 1, 2],
             "description": "0 clean, 1 drift, 2 not decided (the reason is in output)"},
    "meaning": {"type": "string", "description": "the exit code in words"},
    "output": {"description": "the JSON report (docs/REPORT.md), or the refusal as text"}}}
DECIDED = ("Returns exit 0, 1 or 2 and the JSON report. Exit 2 is not a pass: nothing was decided, "
           "and output says why (no label found, a file not read, a tag not compared). Read-only: "
           "it runs git reads only, on the local repository, with no network.")


def tool(name, title, description, properties, required):
    return {"name": name, "title": title, "description": description + " " + DECIDED,
            "annotations": dict(ANNOTATIONS, title=title), "outputSchema": OUTPUT,
            "inputSchema": {"type": "object", "required": ["repo"] + required,
                            "properties": dict(repo=REPO, **properties)}}


TOOLS = [
    tool("would_tag", "Check before tagging",
         "Use BEFORE creating a release tag: would the version that HEAD declares reuse a label "
         "that already names other code in the tags? Exit 1 means do not tag; bump the version first.",
         {}, []),
    tool("check_versions", "Measure all version labels",
         "Use to audit the whole tag history: does each version label name exactly one code state? "
         "For a single release about to be tagged, use would_tag. With one release only, the answer "
         "is not decided (exit 2).",
         {"published_file": {"type": "string",
                             "description": "a local file with the versions actually released, one per "
                                            "line; tags not on it are not counted as publications"},
          "strict": {"type": "boolean",
                     "description": "answer clean only if every tag scanned was compared (default false)"}},
         []),
    tool("explain_label", "Explain a label in drift",
         "Use after check_versions reports drift: lists, for one label, the paths that differ between "
         "the first tag that used it and each other tag that did. For two references you choose, use compare.",
         {"label": {"type": "string",
                    "description": "a version label reported in drift, as written in the report (e.g. 1.0.0)"}},
         ["label"]),
    tool("compare", "Compare two references",
         "Use to compare any two tags or commits you name: their version labels, closures and the paths "
         "that differ. Publication points play no part. Exit 1 when both declare one label and the code differs.",
         {"a": {"type": "string", "description": "the first tag or commit (the reference side)"},
          "b": {"type": "string", "description": "the second tag or commit; paths are listed as changed, only in a, only in b"}},
         ["a", "b"]),
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
                      "serverInfo": {"name": "closure_drift", "version": "1.2.1"}})
        elif method == "tools/list":
            reply(i, {"tools": TOOLS})
        elif method == "tools/call":
            try:
                res = call(p["name"], p.get("arguments") or {})
                reply(i, {"content": [{"type": "text", "text": json.dumps(res, indent=1)}],
                          "structuredContent": res, "isError": False})
            except (KeyError, TypeError) as e:
                reply(i, {"content": [{"type": "text", "text": f"bad call: {e}"}], "isError": True})
        elif method == "ping":
            reply(i, {})
        else:
            reply(i, error={"code": -32601, "message": f"unknown method {method}"})


if __name__ == "__main__":
    main()
