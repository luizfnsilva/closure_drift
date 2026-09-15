#!/usr/bin/env python3
"""Negative fixture: a label-only corpus under ONE label must be flagged, loudly.

The shape this fixture mirrors is real. A production ledger we audited holds 4,756
published records under a single hand-maintained catalogue label, zero of them with a
recorded closure: replay of the originating code states is impossible from the record
alone. A detector that stays quiet on that shape is broken — the whole point of this
tool is that continuous publication under one unchanging label is exactly where drift
lives and exactly where release-based intuitions fail.

The fixture builds a small synthetic git repository with that shape (one declared
label, N commits that each change the published content, no tags) and asserts BOTH
halves of the required behaviour:

  1. default (--at tags): there are no tags, so the tool must REFUSE to answer
     (exit 2, "no_publication_points") and say to rerun with --at commits — never
     print "clean" for a repository whose publication points it cannot see;
  2. --at commits: verdict must be "drift", with exactly 1 label covering N distinct
     closures — the address (input, version) denotes N different published artefacts.

Zero dependencies beyond CPython >= 3.9 and git, same as the tool. Run:

    python3 fixture_label_only.py                  # in the deposit, where the files are flat
    python3 tests/fixture_label_only.py            # in the source repository, where it lives in tests/
    python3 fixture_label_only.py DETECTOR         # test another copy

With no argument the detector is looked for beside this file first, then one directory
up; the first that exists is used. Both paths are printed on refusal, and the detector
that was actually run is named in every outcome — a fixture that does not say what it
measured can pass while measuring something else.

Exit codes, closed set:

    0   the detector behaves on this fixture
    1   the detector failed the fixture, and each failure is listed
    2   the fixture could not run, cause named (no detector found, git missing,
        the detector produced output that is not JSON)
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

N_COMMITS = 12          # small stand-in for the real 4,756; the shape is what matters
LABEL = "2026.perene"   # one hand-maintained label, never bumped


def sh(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def build_fixture(root: str) -> None:
    sh(root, "git", "init", "-q", "-b", "main")
    sh(root, "git", "config", "user.email", "fixture@example.invalid")
    sh(root, "git", "config", "user.name", "fixture")
    Path(root, "package.json").write_text(json.dumps({"name": "label-only-corpus",
                                                      "version": LABEL}) + "\n")
    for i in range(N_COMMITS):
        Path(root, "edition.txt").write_text(f"published edition state {i}\n")
        sh(root, "git", "add", "-A")
        sh(root, "git", "commit", "-q", "-m", f"edition {i}")
        # no tag, ever: publication here is the commit itself


def run_detector(detector: str, repo: str, *extra) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, detector, "--json", *extra],
                          cwd=repo, capture_output=True, text=True)


def laudo(p: subprocess.CompletedProcess, detector: str) -> dict:
    """The detector's JSON, or a named refusal — never a traceback.

    Output that is not JSON means the detector could not be run at all (wrong file, wrong
    interpreter, a crash before it printed). That is not the detector failing the fixture,
    and reporting it as failure would be a defect indistinguishable from a finding.
    """
    try:
        return json.loads(p.stdout)
    except ValueError:
        print("cannot run: %s did not produce JSON (exit %d)." % (detector, p.returncode),
              file=sys.stderr)
        for rotulo, fluxo in (("stdout", p.stdout), ("stderr", p.stderr)):
            trecho = (fluxo or "").strip().splitlines()
            if trecho:
                print("  %s: %s" % (rotulo, trecho[0][:200]), file=sys.stderr)
        raise SystemExit(2)


def resolve_detector() -> str:
    """Beside this file first, then one directory up. Refuse, naming both, if neither exists.

    The deposit stores its files flat: the detector is the SIBLING of this fixture there.
    The source repository keeps this file in tests/: the detector is one directory up. Looking
    only upwards made the deposited fixture unrunnable in the deposit, and — worse — made it
    pass against whatever closure_drift.py happened to sit in the parent directory, without
    ever executing the one deposited beside it.
    """
    if len(sys.argv) > 1:
        return os.path.abspath(sys.argv[1])
    here = Path(__file__).resolve().parent
    tentados = [here / "closure_drift.py", here.parent / "closure_drift.py"]
    for caminho in tentados:
        if caminho.is_file():
            return os.path.abspath(caminho)
    print("cannot run: no closure_drift.py found. Tried, in order:", file=sys.stderr)
    for caminho in tentados:
        print("  %s" % caminho, file=sys.stderr)
    print("Pass the detector explicitly: python3 %s DETECTOR"
          % os.path.basename(__file__), file=sys.stderr)
    raise SystemExit(2)


def identifica(detector: str) -> str:
    with open(detector, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def main() -> int:
    detector = resolve_detector()
    carimbo = identifica(detector)
    failures = []
    with tempfile.TemporaryDirectory() as root:
        build_fixture(root)

        # 1) default at tags: must refuse (exit 2), never report clean.
        p = run_detector(detector, root)
        if p.returncode != 2:
            failures.append(f"default run: expected exit 2 (no publication points), got {p.returncode}")
        else:
            out = laudo(p, detector)
            if out.get("verdict") != "no_publication_points":
                failures.append(f"default run: expected verdict no_publication_points, got {out.get('verdict')!r}")

        # 2) at commits: must flag drift, 1 label, N closures.
        p = run_detector(detector, root, "--at", "commits", "--closure", "edition.txt")
        if p.returncode != 1:
            failures.append(f"--at commits: expected exit 1 (drift), got {p.returncode}")
        else:
            out = laudo(p, detector)
            got = (out.get("verdict"), out.get("labels"),
                   out.get("labels_covering_multiple_closures"),
                   out.get("max_closures_per_label"))
            want = ("drift", 1, 1, N_COMMITS)
            if got != want:
                failures.append(f"--at commits: expected (verdict,labels,drifting,max)={want}, got {got}")

    if failures:
        print(f"FIXTURE FAILED — the detector does not flag a label-only corpus:")
        print(f"  detector: {detector} (sha256 {carimbo})")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"fixture ok: {N_COMMITS} publications under one label -> refused at tags, "
          f"drift (1 label, {N_COMMITS} closures) at commits")
    print(f"  detector: {detector} (sha256 {carimbo})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
