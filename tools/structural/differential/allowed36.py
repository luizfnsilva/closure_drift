#!/usr/bin/env python3
"""§36 gate: every difference between 1.9.0 and the candidate must be one the pre-registration allows.
Allowed: (1) a JSON report gains `"reason_code": ...`; (2) stderr gains a last line `reason: CODE`; (3) a
no-label refusal of --tag changes its first line to name a publish-time writer (am. 2, am. 3). Exit codes must be equal in every call.
    python3 allowed36.py calls.jsonl"""
import collections, json, re, sys

REFUSAL_CODES = {"version_written_at_publish", "version_outside_component", "no_version_source"}
def drop_reason_json(s):
    return re.sub(r',\n "reason_code": "[a-z_]+"', "", s)
def split_reason(err):
    lines = err.rstrip("\n").split("\n")
    m = re.fullmatch(r"reason: ([a-z_]+)", lines[-1]) if lines else None
    return ("\n".join(lines[:-1]) + ("\n" if err.endswith("\n") else ""), m.group(1)) if m else (err, None)
def suffix_of(short, long):
    return long.endswith(short) or short == long
kinds = collections.Counter(); bad = []
for line in open(sys.argv[1]):
    r = json.loads(line)
    if r.get("kind") != "call" or r["same"]:
        continue
    if r["exit"][0] != r["exit"][1]:
        bad.append(("exit", r)); continue
    out_ok = suffix_of(drop_reason_json(r["cand_out"]), r["ref_out"]) or suffix_of(r["cand_out"], r["ref_out"])
    err_c, code = split_reason(r["cand_err"])
    if out_ok and suffix_of(err_c, r["ref_err"]):
        kinds["reason line/key only"] += 1; continue
    if out_ok and code in REFUSAL_CODES and "could not find a version label" in r["ref_err"] and "--tag" in r["args"]:
        kinds["--tag no-label refusal (am. 2)"] += 1; continue
    bad.append(("text", r))
print(dict(kinds), "unexplained:", len(bad))
for why, r in bad[:5]:
    print("---", why, r["args"][-4:], r["exit"]); print("ref_err:", r["ref_err"][-300:]); print("cand_err:", r["cand_err"][-300:])
    print("ref_out:", r["ref_out"][-200:]); print("cand_out:", r["cand_out"][-200:])
sys.exit(1 if bad else 0)
