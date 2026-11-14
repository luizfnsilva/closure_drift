#!/usr/bin/env python3
"""§35 am. 4: reconcile a differential log. Exit 0 only if every count closes and nothing differs
(or, with --expect-differences, only if something differs). Standard library only.
    python3 reconcile.py calls.jsonl [--expect-differences]"""
import collections, json, sys

rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
kind = collections.Counter(r["kind"] for r in rows)
how = collections.Counter(r.get("how") for r in rows if r["kind"] == "seen")
starts = {r["id"] for r in rows if r["kind"] == "start"}
ends = {r["id"] for r in rows if r["kind"] == "end"}
calls = [r for r in rows if r["kind"] == "call"]
not_concluded = starts - ends
seen, compared = kind["seen"], how["compared"]
excluded = how["inner"] + how["module_call"] + how["other"]
self_calls = how["inner"] - 2 * compared
differ = sum(1 for r in calls if not r["same"])
checks = [
    ("seen = compared + excluded", seen == compared + excluded),
    ("compared = start", compared == len(starts)),
    ("start = end + not concluded", len(starts) == len(ends) + len(not_concluded)),
    ("call = end", len(calls) == len(ends)),
    ("inner = 2 x compared + self-calls (self-calls >= 0)", self_calls >= 0),
    ("no harness_error", kind["harness_error"] == 0),
    ("no call left unconcluded", not not_concluded),
]
print(f"seen {seen} = compared {compared} + excluded {excluded} "
      f"(inner {how['inner']}: 2x{compared} + {self_calls} self-calls; module_call {how['module_call']}; other {how['other']})"
      f" + not concluded {len(not_concluded)}")
print(f"start {len(starts)} end {len(ends)} call {len(calls)} harness_error {kind['harness_error']} differ {differ}")
ok = True
for name, good in checks:
    print(("ok    " if good else "FAIL  ") + name)
    ok &= good
want_diff = "--expect-differences" in sys.argv
if want_diff:
    print(("ok    " if differ else "FAIL  ") + "differences found (positive control)")
    ok &= differ > 0
else:
    print(("ok    " if not differ else "FAIL  ") + "zero differences (null control or candidate)")
    ok &= differ == 0
sys.exit(0 if ok else 1)
