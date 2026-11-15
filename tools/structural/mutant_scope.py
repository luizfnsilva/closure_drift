#!/usr/bin/env python3
"""§35 am. 8: does each mutant still produce its defect after a structural change? Static check: apply each
mutation of tests/negative_controls.py to closure_drift.py and list names the mutated function reads that it
neither defines, receives, nor finds at module level or in builtins. Such a mutant would raise NameError
instead of simulating its defect. Exit 1 if any. Standard library only.
    python3 tools/structural/mutant_scope.py [DETECTOR]"""
import ast, builtins, importlib.util, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
det = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "closure_drift.py"
spec = importlib.util.spec_from_file_location("nc", ROOT / "tests/negative_controls.py")
nc = importlib.util.module_from_spec(spec); sys.argv = sys.argv[:1]; spec.loader.exec_module(nc)
src = det.read_text()
def free_names(tree):
    mod = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and False}
    top = set(dir(builtins))
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)): top.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            top |= {(a.asname or a.name).split(".")[0] for a in n.names}
        else:
            top |= {x.id for x in ast.walk(n) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store)}
    out = {}
    for f in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.Lambda))]:
        if not isinstance(f, ast.FunctionDef): continue
        local = {a.arg for a in f.args.args + f.args.kwonlyargs + f.args.posonlyargs}
        if f.args.vararg: local.add(f.args.vararg.arg)
        if f.args.kwarg: local.add(f.args.kwarg.arg)
        for x in ast.walk(f):
            if isinstance(x, ast.Name) and isinstance(x.ctx, (ast.Store, ast.Del)): local.add(x.id)
            elif isinstance(x, ast.arg): local.add(x.arg)
            elif isinstance(x, (ast.FunctionDef, ast.ClassDef)) and x is not f: local.add(x.name)
            elif isinstance(x, ast.ExceptHandler) and x.name: local.add(x.name)
            elif isinstance(x, (ast.Import, ast.ImportFrom)): local |= {(a.asname or a.name).split(".")[0] for a in x.names}
            elif isinstance(x, (ast.Global, ast.Nonlocal)): local |= set(x.names)
        reads = {x.id for x in ast.walk(f) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)}
        out[f.name] = reads - local - top
    return out
base = free_names(ast.parse(src))
bad = 0
for m in nc.MUTANTS:
    mid, changes = m[0], m[2]
    s = src; ok = True
    for ch in changes:
        old, new = (ch[1], ch[2]) if len(ch) == 3 else ch
        if len(ch) == 3 and ch[0] != "closure_drift.py": ok = None; break
        if s.count(old) != 1: ok = False; break
        s = s.replace(old, new)
    if ok is None: continue
    if not ok: print(f"{mid}: anchor does not match once"); bad += 1; continue
    try: fn = free_names(ast.parse(s))
    except SyntaxError as e: print(f"{mid}: does not parse: {e}"); bad += 1; continue
    new = {k: v - base.get(k, set()) for k, v in fn.items() if v - base.get(k, set())}
    if new: print(f"{mid}: reads names it cannot see: {new}"); bad += 1
print(f"{len(nc.MUTANTS)} mutants, {bad} would not simulate their defect")
sys.exit(1 if bad else 0)
