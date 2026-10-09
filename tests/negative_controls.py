#!/usr/bin/env python3
"""Negative controls: the battery must go red on a broken detector (PREREGISTRATION.md §3).

    python3 tests/negative_controls.py [--json OUT]

Each mutant is a copy of the detector with one change. The battery is run against it and the
proof named in the pre-registration must be red. A mutant whose change could not be applied is
a FAILED control, never a skipped one: a control that silently tests nothing is the defect.
One positive control closes the set: against the unmodified detector nothing is red.

Exit 0 when every mutant is caught by its required proof and the positive control holds,
1 otherwise, 2 when the controls could not run.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DETECTOR = HERE.parent / "closure_drift.py"

# id, required red proof, [(text to find, replacement)]
MUTANTS = [
    ("M01", "A03", [('code = {"clean": 0, "drift": 1}.get(verdict, 2)',
                     'code = {"clean": 0, "drift": 1, "inconclusive": 0}.get(verdict, 2)')]),
    ("M02", "C01", [('if e[1] in ("blob", "commit") and self.holds(e[0], e[1] == "blob")]', 'if e[1] in ("blob", "commit") and self.holds(e[0], e[1] == "blob") and e[0].isascii()]')]),
    ("M03", "D14", [('                raise Refusal(f"git cat-file could not read {want} {printable(name[:60])}: {printable(said)}")',
                     '                return b""')]),
    ("M04", "E01", [('    out = []\n    for ch in str(text):',
                     '    return str(text)\n    out = []\n    for ch in str(text):')]),
    ("M05", "F01", [('"-c", "core.fsmonitor=false",\n', '\n')]),
    ("M06", "C04", [('if e[1] in ("blob", "commit") and', 'if e[1] in ("blob",) and')]),
    ("M07", "D02", [('if not isinstance(cfg, dict):', 'if False:')]),
    ("M08", "B01", [('"points_without_label": no_label,', '"points_without_label": 0,')]),
    ("M09", "A02", [('code = {"clean": 0, "drift": 1}.get(verdict, 2)',
                     'code = {"clean": 0, "drift": 0}.get(verdict, 2)')]),
    ("M10", "D15", [('    except Exception as e:  # noqa: BLE001', '    except ZeroDivisionError as e:  # noqa: BLE001')]),
    ("M11", "W02", [('collides = [s["where"] for f, s in by_label.get(label, {}).items() if f != full]',
                     'collides = [][:0]')]),
    ("M12", "T01", [('if tag_globs and not any(fnmatch.fnmatchcase(name, g) for g in tag_globs):', 'if False:')]),
    ("M13", "S01", [(' or (a.strict and (no_label or empty or truncated)) or', ' or')]),
    ("M14", "U02", [('        short, full, nfiles = closure.ids(entries)\n        if nfiles == 0:\n            empty += 1',
                     '        short, full, nfiles = closure.ids(entries)\n        full = short\n        if nfiles == 0:\n            empty += 1')]),
    ("M15", "X04", [('"label_sources": dict(sorted(labels.counts.items())),\n        }',
                     '"label_sources": dict(sorted(labels.counts.items())),\n            "paths": [e[0] for e in closure.members(head_entries)],\n        }')]),
    ("M16", "CMP01", [('    changed = sorted(p for p in ma if p in mb and ma[p] != mb[p])',
                       '    changed = sorted(p for p in ma if False)')]),
    ("M17", "DG01", [('        print("  repository      " + ", ".join(f"{k}={v}" for k, v in DIAGNOSTICS["repository"].items()) + "\\n")',
                      '        print("  repository      " + str(Path(a.repo).resolve()) + "\\n")')]),
    ("M18", "TL05", [('                or (requires & SCM_TOOLS and not string(project.get("version")))',
                      '                or "setuptools_scm" in self.text(blobs, "pyproject.toml")')]),
    ("M19", "CMP01", [('    code = {"identical": 0, "differs_under_two_labels": 0, "differs_under_one_label": 1}.get(verdict, 2)',
                       '    code = {"identical": 0, "differs_under_two_labels": 0, "differs_under_one_label": 0}.get(verdict, 2)')]),
    ("M20", "EX01", [('               or (g.startswith("**/") and fnmatch.fnmatchcase(path, g[3:]))\n', '')]),
    ("M21", "PT01", [('            src = self.sources.find(blobs)',
                      '            src = self.__dict__.setdefault("_once", self.sources.find(blobs))')]),
    ("M22", "TL01", [('            return TAG_SOURCE, None', '            pass')]),
    ("M23", "TL02", [('    return m.group(1) if m else name', '    return name')]),
    ("M24", "VP01", [('        if string(hatch.get("path")):', '        if False:')]),
    ("M25", "PL01", [('        self.values[(oid, how)] = value if plausible(value) else None',
                      '        self.values[(oid, how)] = value')]),
    ("M26", "PL03", [('        if called != "setup":', '        if called is None:')]),
    ("M27", "CV01", [(' or compared < no_label + empty:', ':')]),
    ("M28", "CV02", [(' or compared < no_label + empty:', ' or compared < len(pts):')]),
    ("M29", "AG04", [('if disagree and not agree and not self.fixed)', 'if disagree and not agree)')]),
    ("M30", "AG02", [('tally[0 if nums[0] == tag_nums[0] else 1] += 1', 'tally[0 if label == tag_label(tag) else 1] += 1')]),
    ("M31", "AG12", [('if disagree and not agree and not self.fixed)', 'if disagree and not self.fixed)')]),
    ("M32", "NG02", [('out += value if (not out or value[0] in "-+") else "." + value', 'out += value if not out else "." + value')]),
    ("M34", "AG08", [('    elif contradicted:\n        verdict = "incomplete"\n', '')]),
    ("M35", "AG10", [('and doc.get("private") is True:', 'and doc.get("private") is None:')]),
    ("M36", "EX10", [('return any((is_file and fnmatch.fnmatchcase(name, g[3:])) if g.startswith("**/") and "/" not in g[3:]\n', 'return any(False if False\n')]),
    ("M37", "EX01", [('if g.startswith("**/") and "/" not in g[3:]\n', 'if g.startswith("**/")\n')]),
    ("M38", "CM03", [('else "clean" if all(v == "clean" for v in verdicts)', 'else "clean" if all(v in ("clean", "refused", "no_labels") for v in verdicts)')]),
    ("M39", "CM04", [('    if comps and a.component is not None:\n', '    if False:\n')]),
    ("M40", "CM06", [('        if a.would_tag or a.compare or a.explain is not None:\n', '        if a.compare or a.explain is not None:\n')]),
    # §16 — 1.1.0
    ("M41", "PUB01", [('if published is not None and version_key(name) not in keys and version_key(tag_label(name)) not in keys:',
                       'if False:')]),
    ("M42", "PUB08", [('"tags_included": total, "tags_left_out": left_out}', '"tags_included": total, "tags_left_out": 0}')]),
    ("M43", "PUB09", [('            if self.published is not None and tag and src[0] != TAG_SOURCE:', '            if False:')]),
    ("M44", "VS01", [('("version.txt", "token"),\n                    ("Chart.yaml", "helm"))', '("version.txt", "token"))')]),
    ("M45", "ER01", [('    if not vfile and vsrc is None and not a.would_tag and not any(root_has_source(objects, s) for s, _d, _n in pts):',
                      '    if False:')]),
    ("M46", "ER02", [('    return bool(names & set(ROOT_SOURCES)) or any(n.endswith(".gemspec") for n in names)', '    return False')]),
    ("M47", "EQ01", [('        if label and self.equality == "version":', '        if False:')]),
    ("M48", "MD01", [('mode = b" " + modes.get(path, b"?") if modes is not None else b""', 'mode = b""')]),
    ("M49", "AC01", [('    if at == "commits" and not vfile:', '    if False:')]),
    ("M50", "G05", [('+ (" (commits)" if at == "commits" else "")', '+ ""')]),
    ("M33", "MM03", [('        self.held += len(out) + 1\n', '        self.held += 0\n')]),
]


def battery(detector: Path, work: Path) -> dict | None:
    body = work / "body.json"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    subprocess.run([sys.executable, str(HERE / "battery.py"), str(detector), "--json", str(body)],
                   capture_output=True, env=env)
    try:
        return json.loads(body.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main() -> int:
    out_json = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    source = DETECTOR.read_text(encoding="utf-8")
    rows, bad = [], 0
    for mid, required, changes in MUTANTS:
        work = Path(tempfile.mkdtemp(prefix="cd-mutant-"))
        try:
            mutated, applied = source, True
            for old, new in changes:
                if mutated.count(old) != 1:
                    applied = False
                    break
                mutated = mutated.replace(old, new)
            if not applied:
                status, detail = "not_applied", "the text to change was not found exactly once"
            else:
                target = work / "closure_drift.py"
                target.write_bytes(mutated.encode("utf-8"))
                doc = battery(target, work)
                if doc is None:
                    status, detail = "no_body", "the battery wrote no result"
                else:
                    red = sorted(p["id"] for p in doc["proofs"] if p["status"] == "red")
                    status = "caught" if required in red else "missed"
                    detail = "red: " + (", ".join(red) or "none")
        finally:
            shutil.rmtree(work, ignore_errors=True)
        bad += status != "caught"
        rows.append({"id": mid, "required_red": required, "status": status, "detail": detail})
        print("%-4s must turn %s red   %-11s %s" % (mid, required, status, detail))

    work = Path(tempfile.mkdtemp(prefix="cd-positive-"))
    try:
        doc = battery(DETECTOR, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    red = None if doc is None else sorted(p["id"] for p in doc["proofs"] if p["status"] == "red")
    positive = red == []
    print("P01  unmodified detector      %s" % ("nothing red" if positive else "RED: %s" % red))
    caught = sum(1 for r in rows if r["status"] == "caught")
    if out_json:
        with open(out_json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"mutants": rows, "positive_control_holds": positive}, fh, indent=1, sort_keys=True)
            fh.write("\n")
    print("\n%d mutants · %d caught by the required proof · %d not caught | "
          "positive control %s" % (len(rows), caught, len(rows) - caught,
                                   "holds" if positive else "FAILS"))
    return 0 if bad == 0 and positive else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())
