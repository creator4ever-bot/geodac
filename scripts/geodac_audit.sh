#!/usr/bin/env bash
set -Eeuo pipefail
AST="$HOME/astro"
ENV_PY="$HOME/astroenv/bin/python"
LOG="$AST/logs/geodac_audit_$(date +%F_%H%M%S).log"
mkdir -p "$AST/logs"

exec > >(tee -a "$LOG") 2>&1
echo "== GeoDAC audit @ $(date -Is) =="

if [ -x "$AST/scripts/geodac_quick_context.sh" ]; then
  "$AST/scripts/geodac_quick_context.sh" | tail -n 200
fi

echo; echo "— diagnose_luna_vs_overlay —"
if [ -x "$ENV_PY" ] && [ -f "$AST/diagnose_luna_vs_overlay.py" ]; then
  "$ENV_PY" "$AST/diagnose_luna_vs_overlay.py" | tee "$AST/logs/diag_lvo_last.txt" || true
else
  echo "skip"
fi

echo; echo "— invariants —"
TS="$AST/transits_slow.py"
if [ -f "$TS" ]; then
  if grep -nE "normalize_cusps_to_asc|cusps_peak|houses[[:space:]]*[(][[:space:]]*jd_peak[[:space:]]*[)]" "$TS"; then
    echo "WARN: patterns found"
  else
    echo "OK: none"
  fi
else
  echo "no $TS"
fi

PL="$AST/push_lunar_natal_managed.sh"
if [ -f "$PL" ]; then
  if grep -nE "lunar_angles_postfix\.py|lunar_angles_rehouse\.py" "$PL"; then
    echo "OK: post scripts present"
  else
    echo "WARN: no post scripts"
  fi
else
  echo "no $PL"
fi

echo; echo "— cron —"
crontab -l 2>/dev/null | grep -E "push_eclipses|push_overlay_houses" || echo "no cron lines"

echo; echo "Audit saved to: $LOG"
