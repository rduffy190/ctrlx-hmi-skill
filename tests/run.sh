#!/usr/bin/env bash
# Smoke test for the ctrlx-hmi scripts: builds both worked examples with visugen.py (the single cutter screen and
# the multi-screen kit with its settings page), checks the object counts, and renders every preview scenario.
# It cannot prove an import: only PLC Engineering can (see references/format.md). Exits non-zero on any failure.
set -euo pipefail
# On Windows, python3 is often only the Microsoft Store alias: fall back to python.
python3 -c "" 2>/dev/null || python3() { python "$@"; }
HMI="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

# The templates are not shipped: the user makes them once with make_templates.py (README, "First run").
TPL="${CTRLX_HMI_TEMPLATES:-$HMI/templates}"
if [ ! -f "$TPL/wrapper.export" ] || [ ! -f "$TPL/elements.xml" ]; then
    echo "SKIP: no templates in $TPL. Make them first (README.md, 'First run: create your templates')."
    exit 0
fi

expect() {   # expect <export> <objects>
    local n
    n=$(python3 "$HMI/scripts/visugen.py" "$HMI/references/$1" "$OUT/$1.export" | sed -n 's/.*: \([0-9]*\) objects$/\1/p')
    [ "$n" = "$2" ] && echo "PASS $1: $n objects" || { echo "FAIL $1: expected $2 objects, got '$n'"; exit 1; }
}

expect example_screen_cutter.py 4     # CUT_Main + 3 text lists
expect example_hmi_all.py 6           # TRF_Main, TRF_Cfg + 4 text lists
python3 "$HMI/scripts/preview.py" "$OUT/example_screen_cutter.py.export" "$HMI/references/example_preview_cutter.py" \
    "$OUT/preview" > "$OUT/preview.txt"
n=$(ls "$OUT/preview"/*.svg | wc -l)
[ "$n" -eq 4 ] && echo "PASS preview: $n scenarios rendered" || { echo "FAIL preview: $n SVGs"; exit 1; }
grep -q "Settings" "$OUT/example_hmi_all.py.export" && echo "PASS settings page generated from ST_TransferCfg" \
    || { echo "FAIL no settings page"; exit 1; }
python3 "$HMI/tests/test_make_templates.py"
echo "ALL OK"
