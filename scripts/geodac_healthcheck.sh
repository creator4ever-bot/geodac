#!/usr/bin/env bash
set -euo pipefail
PY="/home/DAC/astroenv/bin/python"
CDIR="$HOME/astro"

fail() { echo "[FAIL] $*"; exit 2; }
warn() { echo "[WARN] $*"; }

echo "[hc] invariants: transits_slow.py must NOT use normalize_cusps_to_asc nor dynamic cusps on peak"
if grep -nE "normalize_cusps_to_asc|cusps_peak|housesKATEX_INLINE_OPENjd_peakKATEX_INLINE_CLOSE" "$CDIR/transits_slow.py" >/dev/null; then
  fail "transits_slow.py: found forbidden patterns"
else
  echo "[OK] transits_slow.py invariants"
fi

echo "[hc] lunar push must call lunar_angles_postfix.py and lunar_angles_rehouse.py"
grep -q "lunar_angles_postfix.py" "$CDIR/push_lunar_natal_managed.sh" || fail "postfix not called"
grep -q "lunar_angles_rehouse.py" "$CDIR/push_lunar_natal_managed.sh" || fail "rehouse not called"
echo "[OK] lunar post-fixes present"

echo "[hc] diagnose lunar vs overlay"
OUT="$("$PY" "$CDIR/diagnose_luna_vs_overlay.py" || true)"
echo "$OUT"
ACC="$(echo "$OUT" | awk 'match($0,/ACC=([0-9.]+)%/,a){print a[1]}' | tail -n1)"
[[ -z "${ACC:-}" ]] && fail "cannot parse ACC"
awk "BEGIN{exit !($ACC==100)}" || fail "ACC != 100 (${ACC}%)"
echo "[OK] ACC=${ACC}%"

echo "[hc] done"
