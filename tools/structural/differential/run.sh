#!/bin/sh
# §35 differential: run the batteries with every detector call compared against the reference.
#   tools/structural/differential/run.sh v1.8.2 OUTDIR
# Needs python3 >= 3.10 (sys.orig_argv). Writes OUTDIR/calls.jsonl and OUTDIR/MANIFEST.
set -eu
REFTAG=$1; OUT=$2; ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
PY=${PYTHON:-python3}
mkdir -p "$OUT/ref"
git -C "$ROOT" show "$REFTAG:closure_drift.py" > "$OUT/ref/closure_drift.py"
"$PY" -m venv "$OUT/venv"
SP=$("$OUT/venv/bin/python" -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")
cp "$ROOT/tools/structural/differential/cd_diffhook.py" "$SP/"
echo "import cd_diffhook" > "$SP/zz_cd_diffhook.pth"
export CD_DIFF_LOG="$OUT/calls.jsonl" CD_DIFF_REF="$OUT/ref/closure_drift.py"
: > "$CD_DIFF_LOG"
cd "$ROOT"
for t in tests/fixture_label_only.py tests/battery.py tests/adversarial.py tests/properties.py; do
  "$OUT/venv/bin/python" "$t" < /dev/null > "$OUT/$(basename "$t").log" 2>&1 && echo "$t ok" || echo "$t exit $?"
done
{
  echo "reference $REFTAG $(git -C "$ROOT" rev-parse "$REFTAG^{commit}") $(shasum -a 256 "$OUT/ref/closure_drift.py" | cut -c1-64)"
  echo "candidate $(git -C "$ROOT" rev-parse HEAD) $(shasum -a 256 "$ROOT/closure_drift.py" | cut -c1-64)"
  echo "hook $(shasum -a 256 "$ROOT/tools/structural/differential/cd_diffhook.py" | cut -c1-64)"
  echo "calls $(grep -c '"kind": "call"' "$CD_DIFF_LOG") differ $(grep -c '"same": false' "$CD_DIFF_LOG") module_calls $(grep -c module_call "$CD_DIFF_LOG")"
  echo "calls.jsonl $(shasum -a 256 "$CD_DIFF_LOG" | cut -c1-64)"
} > "$OUT/MANIFEST"
cat "$OUT/MANIFEST"
