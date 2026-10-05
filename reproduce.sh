#!/bin/sh
# Re-run every claim of the README that a machine can re-run. Needs git and python3; no network
# except with --study or --record.
set -eu
cd "$(dirname "$0")"
step() { printf '\n== %s\n' "$1"; }

step "the script is the one this release names"
python3 tools/verify_deposit.py
python3 tools/conferir_versao.py

step "three batteries"
python3 tests/fixture_label_only.py
python3 tests/battery.py < /dev/null
python3 tests/negative_controls.py < /dev/null
python3 tests/adversarial.py < /dev/null

step "properties against the independent oracle, and their controls"
python3 tests/oracle.py --self-test
python3 tests/properties.py < /dev/null
python3 tests/properties.py --controls < /dev/null

step "the examples and demonstrations in docs/ are what the detector prints"
python3 tools/make_report_examples.py --check
python3 tools/make_demos.py --check

for arg in "$@"; do
  case "$arg" in
    --record) step "the nine files against the published Zenodo record"
              python3 tools/verify_deposit.py --from-zenodo ;;
    --study)  step "the study: 100 clones, several hours, about 30 GB of traffic"
              python3 tools/study/run_study.py && python3 tools/study/make_report.py ;;
    *) echo "unknown option $arg (known: --record, --study)" >&2; exit 2 ;;
  esac
done

printf '\nall steps ended without a failure. Large repositories: .github/workflows/benchmark.yml\n'
