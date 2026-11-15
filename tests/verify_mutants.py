#!/usr/bin/env python3
"""§37 P37-3: each check of closure_verify.py removed once; tests/verify_adversarial.py must fail on every one."""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = open(os.path.join(ROOT, "closure_verify.py"), encoding="utf-8").read()
MUTANTS = [
    ("V01 full id not compared", "full != want_full or ", ""),
    ("V02 short id not compared", ' or key.split("~")[0] != short', ""),
    ("V03 object hash not checked", "if h.hexdigest() != oid:", "if False:"),
    ("V04 replace refs ignored", 'if self.run("for-each-ref", "refs/replace").strip():', "if False:"),
    ("V05 missing object accepted", 'raise Stop(2, "object_missing", f"object {oid} is not in this repository")',
     'raise Stop(1, "closure_mismatch", "x")'),
    ("V06 closure_ids entry not required", "if k not in cids or k not in ccom:", "if False:"),
    ("V07 count not checked", 'if r["labels_covering_multiple_closures"] != len(drift):', "if False:"),
    ("V08 member blobs not hashed", 'repo.check(oid, "blob")', "pass"),
]


def main():
    escaped = 0
    for name, old, new in MUTANTS:
        assert SRC.count(old) == 1, f"{name}: anchor not found exactly once"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(SRC.replace(old, new))
        p = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "verify_adversarial.py")],
                           capture_output=True, env=dict(os.environ, CLOSURE_VERIFY=f.name))
        os.unlink(f.name)
        caught = p.returncode != 0
        escaped += not caught
        print(f"{name:40s} {'caught' if caught else 'ESCAPED'}")
    print(f"\n{len(MUTANTS) - escaped} of {len(MUTANTS)} mutants caught")
    return 1 if escaped else 0


if __name__ == "__main__":
    sys.exit(main())
