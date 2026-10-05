# The three answers, in one minute

```bash
python3 examples/demo.py
```

builds three tiny repositories in a temporary folder — each a `VERSION` file, one source file and
one or two tags — measures them, and deletes them. Expected output:

```
1. CLEAN
    Two releases. The version was bumped, and the code changed.
      tag v1.0.0  VERSION says 1.0.0
      tag v1.1.0  VERSION says 1.1.0
    closure_drift answers: clean (exit 0)   expected: clean (exit 0)   as expected

2. DRIFT
    Two releases. The code changed, and nobody bumped the version:
    the label 1.0.0 now names two different programs.
      tag v1.0.0  VERSION says 1.0.0
      tag v1.0.1  VERSION says 1.0.0
    closure_drift answers: drift (exit 1)   expected: drift (exit 1)   as expected

3. NOT ENOUGH TO TELL
    One release. There is nothing to compare its label with, and the tool says so
    instead of saying 'clean'.
      tag v1.0.0  VERSION says 1.0.0
    closure_drift answers: inconclusive (exit 2)   expected: inconclusive (exit 2)   as expected

All three as expected.
```

The third case is the one worth a second look: with nothing to compare, the answer is *not
determined*, exit `2` — never `clean`.
