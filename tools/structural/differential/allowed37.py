#!/usr/bin/env python3
"""§37 gate: the only difference allowed between 1.10.0 and the candidate is a JSON report gaining
`closure_commits` (an object of 16-hex keys → 40-hex commits, the same keys as `closure_ids`). stderr and exit
codes must be equal in every call.
    python3 allowed37.py calls.jsonl            # exit 0 when every difference is allowed
    python3 allowed37.py calls.jsonl --plant    # positive control: plants forbidden differences, must exit 1"""
import collections, json, re, sys


def allowed(r):
    if r["exit"][0] != r["exit"][1] or r["ref_err"] != r["cand_err"]:
        return False
    try:
        ref, cand = json.loads(r["ref_out"]), json.loads(r["cand_out"])
    except ValueError:
        return False
    if not isinstance(cand, dict) or "closure_commits" not in cand or "closure_commits" in ref:
        return False
    cc = cand.pop("closure_commits")
    if set(cc) != set(cand.get("closure_ids", {})) or not all(re.fullmatch(r"[0-9a-f]{40}", v) for v in cc.values()):
        return False
    return ref == cand


def main():
    calls = [json.loads(l) for l in open(sys.argv[1])]
    calls = [r for r in calls if r.get("kind") == "call" and not r["same"]]
    if "--plant" in sys.argv:
        planted = []
        for r in calls:
            for edit in ("exit", "verdict", "err"):
                p = dict(r, exit=list(r["exit"]))
                if edit == "exit":
                    p["exit"][1] += 1
                elif edit == "verdict":
                    p["cand_out"] = p["cand_out"].replace('"verdict": "drift"', '"verdict": "clean"')
                    if p["cand_out"] == r["cand_out"]:
                        continue
                else:
                    p["cand_err"] = p["cand_err"] + "x"
                planted.append(p)
        calls = planted
    kinds = collections.Counter("allowed" if allowed(r) else "FORBIDDEN" for r in calls)
    print(f"differences: {len(calls)} · " + " · ".join(f"{k} {n}" for k, n in sorted(kinds.items())))
    return 1 if kinds["FORBIDDEN"] else 0


if __name__ == "__main__":
    sys.exit(main())
